# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "pandas",
#     "matplotlib",
# ]
# ///
"""
End-to-end: fetch hourly temperatures for Kloten (CH) and De Bilt (NL),
save them as a CSV, then plot a ridgeline-style week-by-week comparison
(Dutch labels) to both PNG and SVG.

Data sources (both free, no API key required, both hourly resolution):
  - MeteoSwiss Open Data (STAC API), station "KLO" (Kloten/Zürich Airport)
      parameter tre200h0 = hourly mean temperature, 2m above ground
      https://opendatadocs.meteoswiss.ch/
  - KNMI "uurgegevens" (hourly data) service, station 260 (De Bilt)
      variable T = temperature, 0.1 °C, measured at 1.5m
      https://www.knmi.nl/kennis-en-datacentrum/achtergrond/data-ophalen-vanuit-een-script

Note on resolution: MeteoSwiss goes down to 10-minute values with no key
needed; KNMI's free endpoints stop at hourly (their 10-minute data needs a
separate EDR API key). Hourly is used here so both series are comparable.

Usage:
    uv run weather_ridge.py                 # current year, 30 May - 31 Aug
    uv run weather_ridge.py --year 2025
"""

import argparse
import io
import re
import sys
from datetime import date

import pandas as pd
import requests
import matplotlib.pyplot as plt

MS_STATION = "klo"           # MeteoSwiss 3-letter station code for Kloten
KNMI_STATION = 260            # KNMI station number for De Bilt
STAC_ITEM_URL = f"https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn/items/{MS_STATION}"
KNMI_URL = "https://www.daggegevens.knmi.nl/klimatologie/uurgegevens"

SKIP_ISO_WEEKS = {36}         # ISO weeks to leave out of the plot
HALF_RANGE = 13               # fixed +/- degree window per row, so every row is centered the same way

DAY_LABELS_NL = ["ma", "di", "wo", "do", "vr", "za", "zo"]
MONTH_LABELS_NL = {1: "jan", 2: "feb", 3: "mrt", 4: "apr", 5: "mei", 6: "jun",
                    7: "jul", 8: "aug", 9: "sep", 10: "okt", 11: "nov", 12: "dec"}


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch_meteoswiss_hourly(start: date, end: date) -> pd.DataFrame:
    """Hourly mean temperature ('tre200h0') for Kloten -> ['datetime', 'kloten_temp']."""
    r = requests.get(STAC_ITEM_URL, timeout=30)
    r.raise_for_status()
    item = r.json()

    assets = item.get("assets", {})
    # Hourly-granularity CSV assets look like
    # "ogd-smn_klo_h_historical.csv" / "ogd-smn_klo_h_recent.csv" / "ogd-smn_klo_h.csv"
    hourly_assets = [
        a["href"]
        for key, a in assets.items()
        if re.search(rf"ogd-smn_{MS_STATION}_h(_|\.csv$)", key)
    ]
    if not hourly_assets:
        raise RuntimeError(
            f"No hourly CSV asset found for station '{MS_STATION}'. "
            f"Check https://data.geo.admin.ch/browser/index.html#/collections/"
            f"ch.meteoschweiz.ogd-smn/items/{MS_STATION} for the current asset names."
        )

    frames = []
    for href in hourly_assets:
        resp = requests.get(href, timeout=60)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), sep=";")
        df.columns = [c.strip().lower() for c in df.columns]
        frames.append(df)

    df_all = pd.concat(frames, ignore_index=True)
    df_all["datetime"] = pd.to_datetime(df_all["reference_timestamp"], dayfirst=True, errors="coerce")
    df_all = df_all.dropna(subset=["datetime"])
    df_all = df_all[(df_all["datetime"].dt.date >= start) & (df_all["datetime"].dt.date <= end)]

    if "tre200h0" not in df_all.columns:
        raise RuntimeError("Column 'tre200h0' (hourly mean temperature) not found in MeteoSwiss data.")

    out = df_all[["datetime", "tre200h0"]].rename(columns={"tre200h0": "kloten_temp"})
    out["kloten_temp"] = pd.to_numeric(out["kloten_temp"], errors="coerce")
    return out.sort_values("datetime").reset_index(drop=True)


def fetch_knmi_hourly(start: date, end: date) -> pd.DataFrame:
    """Hourly temperature ('T', tenths of °C) for De Bilt -> ['datetime', 'debilt_temp']."""
    payload = {
        "stns": str(KNMI_STATION),
        "start": start.strftime("%Y%m%d") + "01",
        "end": end.strftime("%Y%m%d") + "24",
        "vars": "T",
    }
    r = requests.post(KNMI_URL, data=payload, timeout=60)
    r.raise_for_status()

    lines = r.text.splitlines()
    header = None
    data_lines = []
    for line in lines:
        if line.startswith("#"):
            header = line.lstrip("#").strip()
        elif line.strip():
            data_lines.append(line)

    if header is None or not data_lines:
        raise RuntimeError("Unexpected response format from KNMI uurgegevens endpoint.")

    columns = [c.strip() for c in header.split(",")]
    df = pd.read_csv(io.StringIO("\n".join(data_lines)), names=columns)
    df.columns = [c.strip() for c in df.columns]

    # KNMI hour (HH) runs 1-24 and denotes the hour ENDING at that time,
    # e.g. HH=1 covers 00:00-01:00, HH=24 covers 23:00-24:00 (= next day 00:00).
    base = pd.to_datetime(df["YYYYMMDD"].astype(str), format="%Y%m%d")
    df["datetime"] = base + pd.to_timedelta(df["HH"].astype(int), unit="h")
    df["debilt_temp"] = pd.to_numeric(df["T"], errors="coerce") / 10.0

    return df[["datetime", "debilt_temp"]].sort_values("datetime").reset_index(drop=True)


# --------------------------------------------------------------------------
# Plotting
# --------------------------------------------------------------------------

def fmt_nl(ts) -> str:
    return f"{ts.day:02d} {MONTH_LABELS_NL[ts.month]}"


def plot_ridge(df: pd.DataFrame, out_stem: str):
    iso = df["datetime"].dt.isocalendar()
    df["iso_year"] = iso["year"]
    df["iso_week"] = iso["week"]
    df["day_pos"] = df["datetime"].dt.weekday + df["datetime"].dt.hour / 24.0

    weeks = sorted(
        df[["iso_year", "iso_week"]].drop_duplicates().itertuples(index=False),
        key=lambda t: (t.iso_year, t.iso_week),
    )
    weeks = [wk for wk in weeks if wk.iso_week not in SKIP_ISO_WEEKS]
    n = len(weeks)

    label_bbox = dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.9)

    fig, axes = plt.subplots(n, 1, figsize=(10, 0.78 * n), sharex=True)

    for i, (ax, wk) in enumerate(zip(axes, weeks)):
        week_df = df[(df["iso_year"] == wk.iso_year) & (df["iso_week"] == wk.iso_week)].sort_values("day_pos")

        ax.plot(week_df["day_pos"], week_df["kloten_temp"], color="tab:red", linewidth=1.2, clip_on=False, zorder=3)
        ax.plot(week_df["day_pos"], week_df["debilt_temp"], color="tab:blue", linewidth=1.2, linestyle="--", clip_on=False, zorder=3)

        # center this row's curves around a fixed +/- window so every row aligns the same way
        row_mid = pd.concat([week_df["kloten_temp"], week_df["debilt_temp"]]).mean()
        ax.set_ylim(row_mid - HALF_RANGE, row_mid + HALF_RANGE)

        # single overall min/max marker for the week, across both cities; label placed INSIDE (toward center)
        long_df = week_df.melt(id_vars=["day_pos"], value_vars=["kloten_temp", "debilt_temp"],
                                var_name="city", value_name="temp").dropna(subset=["temp"])
        color_map = {"kloten_temp": "tab:red", "debilt_temp": "tab:blue"}
        if not long_df.empty:
            lo = long_df.loc[long_df["temp"].idxmin()]
            hi = long_df.loc[long_df["temp"].idxmax()]
            for row, dy, va in ((hi, -8, "top"), (lo, 8, "bottom")):
                c = color_map[row["city"]]
                ax.scatter([row["day_pos"]], [row["temp"]], color=c, s=14, zorder=4, clip_on=False)
                ax.annotate(f"{row['temp']:.0f}", (row["day_pos"], row["temp"]), fontsize=8.5, color=c,
                            fontweight="bold", xytext=(0, dy), textcoords="offset points",
                            ha="center", va=va, bbox=label_bbox, zorder=5, annotation_clip=False)

        # legend anchored to each city's first real data point (sits in the first row's empty gap, if any)
        if i == 0:
            for col, color, ls, name in (
                ("kloten_temp", "tab:red", "-", "Kloten (CH)"),
                ("debilt_temp", "tab:blue", "--", "De Bilt (NL)"),
            ):
                first = week_df.dropna(subset=[col]).iloc[0]
                label_x = first["day_pos"] - 0.15
                ax.plot([label_x, first["day_pos"]], [first[col], first[col]], color=color, linestyle=ls,
                         linewidth=0.9, alpha=0.6, clip_on=False, zorder=2)
                ax.text(label_x, first[col], name + "  ", fontsize=9, color=color, fontweight="bold",
                        ha="right", va="center", clip_on=False)

        start_date = fmt_nl(week_df["datetime"].min())
        end_date = fmt_nl(week_df["datetime"].max())
        ax.text(-0.012, 0.62, f"Week {wk.iso_week}", transform=ax.transAxes, fontsize=9,
                fontweight="bold", va="center", ha="right")
        ax.text(-0.012, 0.38, f"{start_date} – {end_date}", transform=ax.transAxes, fontsize=7.5,
                color="gray", va="center", ha="right")

        ax.set_yticks([])
        ax.set_ylabel("")
        ax.patch.set_alpha(0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(axis="x", length=0)

    axes[-1].set_xlim(0, 7)
    axes[-1].set_xticks([d + 0.5 for d in range(7)])
    axes[-1].set_xticklabels(DAY_LABELS_NL)

    fig.suptitle("Uurlijkse temperatuur (°C) – Kloten vs De Bilt", fontsize=13, y=0.94)
    fig.subplots_adjust(hspace=-0.15, top=0.88, left=0.12)

    fig.savefig(f"{out_stem}_ridge.png", dpi=150, bbox_inches="tight", facecolor="white")
    fig.savefig(f"{out_stem}_ridge.svg", bbox_inches="tight", facecolor="white")
    print(f"Saved {out_stem}_ridge.png and {out_stem}_ridge.svg")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=date.today().year, help="Year to fetch (default: current year)")
    args = parser.parse_args()

    start = date(args.year, 7, 1)
    end = date(args.year, 8, 31)

    print(f"Fetching Kloten hourly data from MeteoSwiss ({start} to {end}) ...")
    kloten = fetch_meteoswiss_hourly(start, end)

    print(f"Fetching De Bilt hourly data from KNMI ({start} to {end}) ...")
    debilt = fetch_knmi_hourly(start, end)

    merged = pd.merge(kloten, debilt, on="datetime", how="outer").sort_values("datetime")
    if merged.empty:
        print("No data returned for the requested period.", file=sys.stderr)
        sys.exit(1)

    csv_path = f"kloten_vs_debilt_hourly_{args.year}.csv"
    merged.to_csv(csv_path, index=False)
    print(f"Saved data to {csv_path}")

    plot_ridge(merged, csv_path.rsplit(".", 1)[0])


if __name__ == "__main__":
    main()
