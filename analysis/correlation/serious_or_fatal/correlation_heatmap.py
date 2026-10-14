"""Spearman correlation heatmap: Y (serious/fatal injury rate) and every input.

Reads beat_features.csv (from build_beat_features.py) and keeps beats with
enough known-injury records to give a stable rate.

Outputs:
  correlation_heatmap.png   full matrix, Y in the first row and column
  y_correlations.png        just the Y column, sorted, with significance

Usage (from the repo root):
  python3 analysis/correlation/serious_or_fatal/correlation_heatmap.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

HERE = Path(__file__).resolve().parent

Y = "serious_fatal_rate"

# Column -> label, grouped. Groups are separated by lines on the heatmap.
GROUPS = {
    "Outcome": {
        Y: "Y: serious/fatal injury rate",
    },
    "Who is involved": {
        "pct_pedestrian": "% pedestrians",
        "pct_bicyclist": "% bicyclists",
        "pct_motorcyclist": "% motorcyclists",
        "pct_heavy_vehicle": "% trucks and buses",
        "persons_per_collision": "People per collision",
        "pct_injury_known": "% with known injury level",
    },
    "When and why": {
        "collisions_per_year": "Collisions per year",
        "collisions_per_street_mile": "Collisions per street mile",
        "pct_night": "% at night (8pm-6am)",
        "pct_weekend": "% on weekends",
        "pct_hit_and_run": "% hit-and-run",
        "pct_unsafe_speed": "% unsafe speed",
        "pct_dui": "% DUI",
        "pct_red_light": "% red light",
        "pct_ped_right_of_way": "% pedestrian right-of-way",
        "pct_unsafe_turn": "% unsafe turn",
        "pct_possible_freeway": "% possibly on freeway",
    },
    "Streets": {
        "mean_speed_limit": "Mean speed limit",
        "pct_40mph_plus": "% street miles 40+ mph",
        "pct_arterial": "% arterial street miles",
        "pct_one_way": "% one-way street miles",
        "street_miles_per_sq_mi": "Street miles per sq mi",
        "intersections_per_sq_mi": "Intersections per sq mi",
        "freeway_miles": "Freeway miles",
        "median_daily_traffic": "Median daily traffic (ADT)",
        "bikeway_miles_per_street_mile": "Bikeway miles per street mile",
    },
    "Land use": {
        "area_sq_mi": "Beat area (sq mi)",
        "transit_stops_per_sq_mi": "Transit stops per sq mi",
        "parking_meters_per_sq_mi": "Parking meters per sq mi",
        "pct_commercial_zoning": "% commercial zoning",
        "pct_industrial_zoning": "% industrial zoning",
    },
    "Residents": {
        "pop_per_sq_mi": "Population per sq mi",
        "median_hh_income": "Median household income",
        "pct_poverty": "% in poverty",
        "pct_zero_vehicle_hh": "% households with no car",
        "pct_walk_to_work": "% walk to work",
        "pct_bike_to_work": "% bike to work",
        "pct_transit_to_work": "% transit to work",
        "pct_work_from_home": "% work from home",
        "pct_age_65_plus": "% age 65+",
        "pct_under_18": "% under 18",
        "pct_hispanic": "% Hispanic or Latino",
    },
    "Crime": {
        "violent_crime_per_1k": "Violent crimes per 1k residents",
        "dui_arrests_per_1k": "DUI offenses per 1k residents",
    },
}
LABELS = {col: label for group in GROUPS.values() for col, label in group.items()}

# Diverging blue <-> red with a neutral gray midpoint
CMAP = LinearSegmentedColormap.from_list(
    "blue_red", ["#104281", "#2a78d6", "#f0efec", "#e34948", "#8f1d1d"]
)
INK = "#1f1f1e"
MUTED = "#6b6b66"
SURFACE = "#fcfcfb"


def load():
    table = pd.read_csv(HERE / "beat_features.csv", dtype={"beat": str})
    table = table[table["in_analysis"]]
    return table[list(LABELS)]


def y_table(data):
    rows = []
    for col in data.columns.drop(Y):
        pair = data[[Y, col]].dropna()
        rho, p = stats.spearmanr(pair[Y], pair[col])
        r, p_r = stats.pearsonr(pair[Y], pair[col])
        rows.append({
            "variable": col, "label": LABELS[col], "spearman_rho": rho, "spearman_p": p,
            "pearson_r": r, "pearson_p": p_r, "n_beats": len(pair),
        })
    out = pd.DataFrame(rows).sort_values("spearman_rho", key=abs, ascending=False)
    return out.round(4)


def cell_text_color(value):
    return "white" if abs(value) >= 0.55 else INK


def full_heatmap(corr, n_beats):
    k = len(corr)
    fig, ax = plt.subplots(figsize=(20, 18), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    lower = np.tril(np.ones((k, k), dtype=bool))
    masked = np.ma.masked_where(~lower, corr.to_numpy())
    im = ax.imshow(masked, cmap=CMAP, vmin=-1, vmax=1)

    for i in range(k):
        for j in range(i + 1):
            v = corr.iat[i, j]
            ax.text(j, i, f"{v:.2f}".replace("0.", ".").replace("-.", "−."),
                    ha="center", va="center", fontsize=5.5, color=cell_text_color(v))

    labels = [LABELS[c] for c in corr.columns]
    ax.set_xticks(range(k), labels, rotation=90, fontsize=8, color=INK)
    ax.set_yticks(range(k), labels, fontsize=8, color=INK)
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.get_xticklabels()[0].set_fontweight("bold")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Group separators and the Y row outline
    edge = 0
    for group in list(GROUPS.values())[:-1]:
        edge += len(group)
        ax.plot([edge - 0.5, edge - 0.5], [edge - 0.5, k - 0.5], color=SURFACE, lw=3)
        ax.plot([-0.5, edge - 0.5], [edge - 0.5, edge - 0.5], color=SURFACE, lw=3)
    ax.add_patch(plt.Rectangle((-0.5, -0.5), 1, k, fill=False, ec=INK, lw=1.2))

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cbar.set_label("Spearman correlation", color=INK)
    cbar.outline.set_visible(False)
    ax.set_title(
        "Serious/fatal injury rate and beat characteristics: Spearman correlations\n"
        f"San Diego police beats, 2018–2025 (n = {n_beats} beats with ≥ 50 known-injury records)",
        fontsize=14, color=INK, loc="left", pad=16,
    )
    fig.savefig(HERE / "correlation_heatmap.png", dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


def y_heatmap(ytab, n_beats):
    ytab = ytab.sort_values("spearman_rho", ascending=False)
    k = len(ytab)
    fig, ax = plt.subplots(figsize=(5, 13), facecolor=SURFACE)
    vals = ytab["spearman_rho"].to_numpy()[:, None]
    ax.imshow(vals, cmap=CMAP, vmin=-1, vmax=1, aspect="auto")
    for i, (rho, p) in enumerate(zip(ytab["spearman_rho"], ytab["spearman_p"])):
        stars = "**" if p < 0.01 else "*" if p < 0.05 else ""
        ax.text(0, i, f"{rho:+.2f}{stars}", ha="center", va="center", fontsize=9, color=cell_text_color(rho))
    ax.set_yticks(range(k), ytab["label"], fontsize=9, color=INK)
    ax.set_xticks([0], ["Y: serious/fatal\ninjury rate"], fontsize=9, color=INK)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(
        f"Correlation with Y, sorted\nSpearman, n = {n_beats} beats; * p < .05, ** p < .01",
        fontsize=11, color=INK, loc="left", pad=36,
    )
    fig.savefig(HERE / "y_correlations.png", dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


def main():
    data = load()
    corr = data.corr(method="spearman")
    ytab = y_table(data)
    full_heatmap(corr, len(data))
    y_heatmap(ytab, len(data))
    print(ytab[["label", "spearman_rho", "spearman_p", "pearson_r", "n_beats"]].to_string(index=False))


if __name__ == "__main__":
    main()
