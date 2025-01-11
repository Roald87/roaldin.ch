# /// script
# requires-python = "~=3.12"
# dependencies = [
#    "pandas==2.2.3",
#    "altair==5.5.0",
#    "vl-convert-python==1.7.0"
# ]
# ///

import pandas as pd
import altair as alt

if __name__ == '__main__':
    # Load the CSV file
    input_file = "je-e-05.07.03_output.csv"
    df = pd.read_csv(input_file, sep=";")

    df["Label"] = df["Label"].str.replace(r"\s*\d+\)$", "", regex=True)

    # Translation dictionary
    translation_dict = {
        "Meat": "Vlees",
        "Hospital Services": "Ziekenhuisdiensten",
        "Education": "Onderwijs",
        "Bread and cereals": "Brood en granen",
        "Fish": "Vis",
        # "Other food": "Overig eten",
        "Health": "Gezondheid",
        "Food": "Eten",
        "Alcoholic beverages": "Alcoholische dranken",
        "Recreation and culture": "Recreatie en cultuur",
        "Restaurants and hotels": "Restaurants en hotels",
        "Clothing": "Kleding",
        "Footwear": "Schoeisel",
        "Transport services": "Vervoersdiensten",
        "Non-alcoholic beverages": "Niet-alcoholische dranken",
        "Households appliances": "Huishoudelijke apparaten",
        "Tobacco": "Tabak",
        "Personal transport equipment": "Persoonlijk vervoersmateriaal",
        "Audio-visual, photographic and information processing equipment": "Audiovisueel, foto en IT",
        "Electricity gas and other fuels": "Elektriciteit, gas en andere brandstoffen"
    }

    labels_of_interest_english = list(translation_dict.keys())
    df_filtered = df[df["Label"].isin(labels_of_interest_english)]

    df_filtered["Ratio"] = df_filtered["Switzerland"] / df_filtered["Netherlands"]

    df_filtered["Label"] = df_filtered["Label"].map(translation_dict)

    # Get the value in 2023 to sort by
    df_2023 = df_filtered[df_filtered["Year"] == 2023]
    df_2023_sorted = df_2023.sort_values("Ratio", ascending=False)

    # Create a categorical ordering based on the sorted labels
    ordered_labels = df_2023_sorted["Label"]

    # Calculate dynamic y-axis limits with a 50% margin
    y_min = df_filtered["Ratio"].min()
    y_max = df_filtered["Ratio"].max()

    # Define the ratio chart with dynamic y-axis limits
    ratio_chart = alt.Chart().mark_line().encode(
        x=alt.X("Year:O", axis=alt.Axis(
            ticks=True,
            values=[df_filtered["Year"].min(), df_filtered["Year"].max()],
            labelAngle=0,
            title="Jaar",
        )),
        y=alt.Y("Ratio:Q", title=None, sort=ordered_labels, scale=alt.Scale(domain=[y_min, y_max]))
    ).properties(
        height=75,
        width=150
    )

    # Define the gray band
    gray_band = alt.Chart(pd.DataFrame({"min": [1], "max": [2]})).mark_rect(
        color="lightgray",
    ).encode(
        y="min:Q",
        y2="max:Q"
    )

    # Define the circle mark for the 2023 value
    circle_2023 = alt.Chart().mark_circle(
        size=50,
        opacity=1
    ).transform_filter(
        "datum.Year == 2023"
    ).encode(
        x=alt.X("Year:O", axis=alt.Axis(ticks=True, values=[df_filtered["Year"].min(), df_filtered["Year"].max()])),
        y=alt.Y("Ratio:Q", axis=alt.Axis(ticks=True, values=[1, 2]))
    )

    # Define the text mark to display the ratio value next to the circle
    text_2023 = alt.Chart().mark_text(
        align="left", dx=5, fontSize=10
    ).transform_filter(
        "datum.Year == 2023"
    ).encode(
        x=alt.X("Year:O", axis=alt.Axis(ticks=True, values=[df_filtered["Year"].min(), df_filtered["Year"].max()])),
        y=alt.Y("Ratio:Q", axis=alt.Axis(ticks=True, values=[1, 2])),
        text=alt.Text("Ratio:Q", format=".2f")
    )

    # Layer the charts with gray band, reference line, ratio chart, circle, and text
    chart = alt.layer(
        gray_band, ratio_chart, circle_2023, text_2023, data=df_filtered
    ).facet(
        facet=alt.Facet("Label:N", sort=ordered_labels),
        columns=3,
        spacing={"row": 0, "column": 10},
        title='Kostenverhouding van diensten en producten Zwitserland/Nederland'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        domain=False,
        grid=False,
    ).configure_headerFacet(
        labelAnchor='start',
        labelPadding=-5,
        labelFontSize=12,
        title=None,
    )

    chart.save("duur-land-1.svg", scale_factor=1.5)
