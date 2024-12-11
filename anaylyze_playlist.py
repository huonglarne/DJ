import argparse

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, cnames, to_hex


def get_pd_from_xml(xml, target_fields, result_fields):
    playlist_ordered_items = (
        xml.split("<key>Playlist Items</key>")[1]
        .split("</array>")[0]
        .split("<dict>")[1:]
    )

    ids_playlist_order = []
    for each in playlist_ordered_items:
        track_id = each.split("<key>Track ID</key><integer>")[1].split("</integer>")[0]
        ids_playlist_order.append(int(track_id))

    tracks = (
        xml.split("<key>Tracks</key>")[1]
        .split("<key>Playlists</key>")[0]
        .split("<dict>")[2:]
    )

    rows = []
    for each in tracks:
        values = {}

        for field in target_fields:
            x = each.split(f"<key>{field}</key>")

            if len(x) == 1:
                tmp = ""

            else:
                x = x[1]

                if x.startswith("<string>"):
                    tmp = x.split("<string>")[1].split("</string>")
                elif x.startswith("<integer>"):
                    tmp = x.split("<integer>")[1].split("</integer>")
                elif x.startswith("<date>"):
                    tmp = x.split("<date>")[1].split("</date>")

            if tmp:
                tmp = tmp[0]
            else:
                tmp = ""

            values[field] = tmp

        rows.append(dict(values))

    df = pd.DataFrame(rows)

    df["Energy"] = df["Rating"].apply(lambda x: f"{int(int(x)/100*5)}/5" if x else "")

    df = df.drop("Rating", axis=1)

    df["Track ID"] = df["Track ID"].astype(int)
    df["BPM"] = df["BPM"].apply(lambda x: int(x) if x else 0)

    df = df.set_index("Track ID")

    df = df.loc[ids_playlist_order]

    df = df.reset_index(drop=False)
    df.index = df.index + 1

    # remove rountine songs wuth tempo 1
    df = df[df["BPM"] >= 1]


    df = df[result_fields]

    return df


def _rescale(values, new_min=0, new_max=1):
    old_min = min(values)
    old_max = max(values)
    
    # Min-Max Scaling Formula: new_value = ((value - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
    rescaled_values = [(new_max - new_min) * (v - old_min) / (old_max - old_min) + new_min for v in values]
    
    return rescaled_values


def draw_flow_chart(dataframe, file):
    df = dataframe.copy()

    temperature_values = df["Comments"].apply(lambda x: x.split(",")[0] if x else 0)

    

    bpm_color = "blue"
    energy_color = "orange"

    df["Energy"] = (
        df["Energy"]
        .apply(lambda x: int(x.split("/")[0]) if x else 0)
    )

    
    highest_bpm = df["BPM"].max()
    highest_bpm_index = df["BPM"].idxmax()

    lowest_bpm = df["BPM"].min()
    lowest_bpm_index = df["BPM"].idxmin()

    average_bpm = df["BPM"].mean()
    df["BPM"] = df["BPM"].apply(lambda x: x / average_bpm)
    # rescale between 1 and 5
    df["BPM"] = _rescale(df["BPM"], 1, 5)


    x = df.plot(
        x="Name",
        y=["BPM", "Energy"],
        title="BPM and Energy Flow",
        legend=True,
        color=[bpm_color, energy_color],
    )

    x.set_yticks(range(1, 6))

    plt.xticks(rotation=-90)
    plt.xticks(range(0, len(df)), df["Name"], fontsize=8)
    plt.grid()

    # label x axis
    plt.xlabel("")

    # label value of highest and lowest tempo at
    plt.text(
        lowest_bpm_index,
        0.9,
        f"Lowest BPM: {lowest_bpm}",
        verticalalignment="center",
        horizontalalignment="center",
        color=bpm_color,
        fontsize=8,
    )

    plt.text(
        highest_bpm_index,
        5.1,
        f"Highest BPM: {highest_bpm}",
        verticalalignment="center",
        horizontalalignment="center",
        color=bpm_color,
        fontsize=8,
    )

    plt.bar(
        range(0, len(temperature_values)),
        [5 if x == "bright" else 0 for x in temperature_values],
        color="yellow",
        alpha=0.2,
        width=1,
    )

    plt.bar(
        range(0, len(temperature_values)),
        [5 if x == "dark" else 0 for x in temperature_values],
        color="violet",
        alpha=0.3,
        width=1,
    )

    x.get_figure().savefig(file.replace(".xml", "_flow.png"), bbox_inches="tight")


def draw_tempo_range(dataframe, file):
    df = dataframe.copy()

    df = df[df["Energy"] != ""]

    ranges = list(range(105, 210, 5))

    tempo_range_count = (
        df.groupby([pd.cut(df["BPM"], ranges), "Energy"], observed=False)
        .count()
        .drop(["Grouping", "Comments", "Artist", "BPM"], axis=1)
    )
    tempo_range_count = tempo_range_count.rename(columns={"Name": "Num songs"})
    tempo_range_count = tempo_range_count.reset_index(drop=False)

    energy_categories = df["Energy"].unique().tolist()
    energy_categories = sorted(energy_categories)

    tempo_groups = tempo_range_count["BPM"].unique().tolist()

    n = len(energy_categories)
    limit_colors = [cnames["wheat"], cnames["blue"]]
    cmap = LinearSegmentedColormap.from_list(
        "green_orange", limit_colors, N=n, gamma=1.3
    )
    hex_colors = [to_hex(cmap(i / (n - 1))) for i in range(n)]

    plt.clf()

    prev_num_song_values = [0] * len(tempo_groups)
    y = range(len(tempo_groups))

    for energy, color in zip(energy_categories, hex_colors):
        num_song_values = tempo_range_count[tempo_range_count["Energy"] == energy][
            "Num songs"
        ]
        plt.barh(
            y, num_song_values, left=prev_num_song_values, label=energy, color=color
        )
        prev_num_song_values = [
            x + y for x, y in zip(prev_num_song_values, num_song_values)
        ]

    plt.yticks(y, tempo_groups)
    plt.legend(title="Energy")
    plt.title("BPM - Energy Count")
    plt.xlabel("Number of songs")
    plt.ylabel("BPM Range")
    plt.tight_layout()

    plt.savefig(
        file.replace(".xml", "_bpm_energy_count.png"), bbox_inches="tight"
    )


parser = argparse.ArgumentParser(
    description="Parse Apple Music iTunes Playlist XML file"
)
parser.add_argument(
    "--file",
    type=str,
    help="Apple Music iTunes Playlist XML file",
    default="L-L-Lindy by Huong.xml",
    nargs="?",
)


if __name__ == "__main__":
    args = parser.parse_args()

    file = args.file

    with open(file, "r", encoding="utf-8") as f:
        xml = f.read()

    target_fields = [
        "Track ID",
        "Name",
        "Artist",
        "Grouping",
        "BPM",
        "Comments",
        "Rating",
        "Sort Artist",
        "Release Date",
    ]

    result_fields = [
        "Name",
        "BPM",
        "Energy",
        "Grouping",
        "Comments",
        "Artist",
        "Release Date",
    ]

    dataframe = get_pd_from_xml(xml, target_fields, result_fields)

    dataframe.to_excel(file.replace(".xml", ".xlsx"), index=True)

    draw_flow_chart(dataframe, file)

    draw_tempo_range(dataframe, file)
