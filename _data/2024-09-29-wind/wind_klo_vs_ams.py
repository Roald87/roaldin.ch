# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "pandas",
#     "matplotlib",
# ]
# ///
"""
End-to-end: fetch daily mean wind speed for Zurich/Kloten (CH) and
Amsterdam/Schiphol (NL), save as CSV, then plot the average wind speed
over the year (rolling 31-day window climatology) to both PNG and SVG.

Data sources (both free, no API key required, both daily resolution):
  - MeteoSwiss Open Data (STAC API), station "KLO" (Kloten/Zurich Airport)
      parameter fu3010d0 = wind speed scalar, daily mean, km/h
      https://opendatadocs.meteoswiss.ch/
  - KNMI "daggegevens" (daily data) service, station 240 (Schiphol/Amsterdam)
      variable FG = daily mean wind speed, in 0.1 m/s
      https://www.knmi.nl/kennis-en-datacentrum/achtergrond/data-ophalen-vanuit-een-script

Usage:
    uv run wind_klo_vs_ams.py                       # fetch + save + plot, 1980-2025
    uv run wind_klo_vs_ams.py --start 1980 --end 2025
    uv run wind_klo_vs_ams.py --plot-only --csv wind_klo_vs_ams_1980_2025.csv
"""

import argparse
import io
import sys
from datetime import date

import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patheffects as pe

MS_STATION = "klo"    # MeteoSwiss 3-letter station code for Kloten (Zurich)
KNMI_STATION = 240     # KNMI station number for Schiphol (Amsterdam)
KNMI_URL = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"
STAC_ITEM_URL = f"https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn/items/{MS_STATION}"

ROLLING_WINDOW = 31   # days, matches the original WeatherSpark-style chart


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch_meteoswiss_daily_wind(start: date, end: date) -> pd.DataFrame:
    """Daily mean wind speed ('fu3010d0', km/h) for Kloten -> ['date', 'zurich_wind']."""
    r = requests.get(STAC_ITEM_URL, timeout=30)
    r.raise_for_status()
    item = r.json()

    assets = item.get("assets", {})
    daily_assets = [
        a["href"]
        for key, a in assets.items()
        if key in (f"ogd-smn_{MS_STATION}_d_historical.csv", f"ogd-smn_{MS_STATION}_d_recent.csv")
    ]
    if not daily_assets:
        raise RuntimeError(f"No daily CSV asset found for station '{MS_STATION}'.")

    frames = []
    for href in daily_assets:
        resp = requests.get(href, timeout=60)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), sep=";", encoding="latin1")
        df.columns = [c.strip().lower() for c in df.columns]
        frames.append(df)

    df_all = pd.concat(frames, ignore_index=True)
    df_all["date"] = pd.to_datetime(df_all["reference_timestamp"], dayfirst=True, errors="coerce").dt.normalize()
    df_all = df_all.dropna(subset=["date"])
    df_all = df_all.drop_duplicates(subset="date", keep="last")
    df_all = df_all[(df_all["date"].dt.date >= start) & (df_all["date"].dt.date <= end)]

    if "fu3010d0" not in df_all.columns:
        raise RuntimeError("Column 'fu3010d0' (daily mean wind speed) not found in MeteoSwiss data.")

    out = df_all[["date", "fu3010d0"]].rename(columns={"fu3010d0": "zurich_wind"})
    out["zurich_wind"] = pd.to_numeric(out["zurich_wind"], errors="coerce")
    return out.sort_values("date").reset_index(drop=True)


def fetch_knmi_daily_wind(start: date, end: date) -> pd.DataFrame:
    """Daily mean wind speed ('FG', 0.1 m/s) for Schiphol -> ['date', 'amsterdam_wind'] in km/h."""
    payload = {
        "stns": str(KNMI_STATION),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "vars": "FG",
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
        raise RuntimeError("Unexpected response format from KNMI daggegevens endpoint.")

    columns = [c.strip() for c in header.split(",")]
    df = pd.read_csv(io.StringIO("\n".join(data_lines)), names=columns)
    df.columns = [c.strip() for c in df.columns]

    df["date"] = pd.to_datetime(df["YYYYMMDD"].astype(str), format="%Y%m%d")
    # FG is in 0.1 m/s -> convert to km/h: (value / 10) * 3.6
    df["amsterdam_wind"] = pd.to_numeric(df["FG"], errors="coerce") / 10.0 * 3.6

    return df[["date", "amsterdam_wind"]].sort_values("date").reset_index(drop=True)


def download_and_save_data(start_year: int, end_year: int) -> str:
    """Fetch both stations' daily wind data, merge, and save to CSV. Returns the CSV path."""
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)

    print(f"Fetching Kloten daily wind data from MeteoSwiss ({start} to {end}) ...")
    zurich_df = fetch_meteoswiss_daily_wind(start, end)

    print(f"Fetching Schiphol daily wind data from KNMI ({start} to {end}) ...")
    amsterdam_df = fetch_knmi_daily_wind(start, end)

    merged = pd.merge(zurich_df, amsterdam_df, on="date", how="outer").sort_values("date")
    if merged.empty:
        print("No data returned for the requested period.", file=sys.stderr)
        sys.exit(1)

    csv_path = f"wind_klo_vs_ams_{start_year}_{end_year}.csv"
    merged.to_csv(csv_path, index=False)
    print(f"Saved data to {csv_path}")
    return csv_path


# --------------------------------------------------------------------------
# Climatology
# --------------------------------------------------------------------------

def day_of_year_climatology(df: pd.DataFrame, value_col: str) -> pd.Series:
    """Average value per calendar day (mm-dd, Feb 29 folded into Feb 28), then a
    circular rolling mean over ROLLING_WINDOW days so the start/end of the year
    connect smoothly."""
    d = df.copy()
    d["mmdd"] = d["date"].dt.strftime("%m-%d")
    d.loc[d["mmdd"] == "02-29", "mmdd"] = "02-28"

    daily_mean = d.groupby("mmdd")[value_col].mean()

    ref_year = 2001  # non-leap year, just used to get a clean 365-day x-axis
    idx = pd.date_range(f"{ref_year}-01-01", f"{ref_year}-12-31", freq="D")
    ordered = daily_mean.reindex(idx.strftime("%m-%d")).values
    s = pd.Series(ordered, index=idx)

    # circular rolling mean: pad both ends with wrap-around data
    pad = ROLLING_WINDOW // 2
    padded = pd.concat([s.iloc[-pad:], s, s.iloc[:pad]])
    smoothed = padded.rolling(ROLLING_WINDOW, center=True, min_periods=1).mean()
    return smoothed.iloc[pad:-pad]


# --------------------------------------------------------------------------
# Plotting
# --------------------------------------------------------------------------

def plot_wind(zurich: pd.Series, amsterdam: pd.Series, start_year: int, end_year: int, out_stem: str):
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    ax.plot(amsterdam.index, amsterdam.values, color="tab:blue", linewidth=2)
    ax.plot(zurich.index, zurich.values, color="tab:red", linewidth=2)

    # series names placed directly next to the lines instead of a legend
    label_x = amsterdam.index[10]
    ax.text(label_x, amsterdam.iloc[10] - 1.3, "Schiphol", color="tab:blue",
            fontsize=14, fontweight="bold", ha="left", va="top")
    ax.text(zurich.index[10], zurich.iloc[10] - 1.3, "Kloten", color="tab:red",
            fontsize=14, fontweight="bold", ha="left", va="top")

    # min/max markers: a dot on the line, with the value labeled above it
    outline = [pe.withStroke(linewidth=3, foreground="white")]
    for series, color in ((amsterdam, "tab:blue"), (zurich, "tab:red")):
        for i in (series.idxmax(), series.idxmin()):
            ax.plot(i, series.loc[i], marker="o", markersize=6, color=color, zorder=5)
            ax.annotate(f"{series.loc[i]:.1f}", xy=(i, series.loc[i]),
                        xytext=(0, 9), textcoords="offset points",
                        ha="center", va="bottom", fontsize=13, fontweight="bold",
                        color=color, path_effects=outline)

    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=16))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", length=0, labelsize=12)
    ax.set_xlim(zurich.index.min() - pd.Timedelta(days=4), zurich.index.max() + pd.Timedelta(days=4))

    ax.set_ylim(bottom=0)
    ax.yaxis.set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.set_title("Gemiddelde windsnelheid (km/h)", fontsize=16, pad=26)
    ax.text(0.5, 1.03, f"rollend 31-dagen venster ({start_year}-{end_year})",
            transform=ax.transAxes, ha="center", va="bottom",
            fontsize=11, color="gray")
    fig.tight_layout()

    fig.savefig(f"{out_stem}.png", dpi=150, bbox_inches="tight", transparent=True)
    fig.savefig(f"{out_stem}.svg", bbox_inches="tight", transparent=True)
    print(f"Saved {out_stem}.png and {out_stem}.svg")


def plot_data_from(csv_path: str):
    """Load a previously saved CSV and produce the climatology plot from it."""
    merged = pd.read_csv(csv_path, parse_dates=["date"])

    start_year = int(merged["date"].dt.year.min())
    end_year = int(merged["date"].dt.year.max())

    zurich_clim = day_of_year_climatology(merged.dropna(subset=["zurich_wind"]), "zurich_wind")
    amsterdam_clim = day_of_year_climatology(merged.dropna(subset=["amsterdam_wind"]), "amsterdam_wind")

    plot_wind(zurich_clim, amsterdam_clim, start_year, end_year, "wind_klo_vs_ams")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1980, help="Start year (default: 1980)")
    parser.add_argument("--end", type=int, default=2025, help="End year, inclusive (default: 2025)")
    parser.add_argument("--plot-only", action="store_true",
                         help="Skip fetching; just plot from an existing CSV (see --csv)")
    parser.add_argument("--csv", type=str, default=None,
                         help="CSV path to plot from when using --plot-only "
                              "(default: wind_klo_vs_ams_<start>_<end>.csv)")
    args = parser.parse_args()

    if args.plot_only:
        csv_path = args.csv or f"wind_klo_vs_ams_{args.start}_{args.end}.csv"
        plot_data_from(csv_path)
    else:
        csv_path = download_and_save_data(args.start, args.end)
        plot_data_from(csv_path)


if __name__ == "__main__":
    main()
