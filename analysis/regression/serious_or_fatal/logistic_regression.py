"""Logistic regression: what raises a person's chance of serious or fatal injury?

One row per person in a collision, 2018-2025, whose injury level is known.
Y = serious_or_fatal (1 = serious, severe or fatal; 0 = minor injury).

Inputs are about the person, the crash, and the police beat where it
happened. Beat inputs come from the correlation step, so run
analysis/correlation/serious_or_fatal/build_beat_features.py first.

Outputs:
  odds_ratios.csv        odds ratio, 95% CI and p-value for each input
  odds_ratios.png        the same as a chart
  model_summary.txt      full statsmodels output, fit checks, fatal-only model

Usage (from the repo root):
  python3 analysis/regression/serious_or_fatal/logistic_regression.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.metrics import roc_auc_score
from statsmodels.stats.outliers_influence import variance_inflation_factor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
BEAT_FILE = ROOT / "analysis/correlation/serious_or_fatal/beat_features.csv"

START_YEAR = 2018
END_YEAR = 2025

MOTORCYCLE_TYPES = {"Motorcycle", "Motor Driven Cycle/Scooter"}
HEAVY_WORDS = "Truck|Semi|Bus|Tractor|Trailer"

# Model term -> plain-language label, in display order
LABELS = {
    "C(road_user)[T.Passenger]": "Passenger (vs driver)",
    "C(road_user)[T.Pedestrian]": "Pedestrian (vs driver)",
    "C(road_user)[T.Bicyclist]": "Bicyclist (vs driver)",
    "C(road_user)[T.Motorcyclist]": "Motorcyclist (vs driver)",
    "C(road_user)[T.Other]": "Other road user (vs driver)",
    "heavy_vehicle": "Truck or bus involved",
    "night": "Night (8pm-6am)",
    "weekend": "Weekend",
    "unsafe_speed": "Cause: unsafe speed",
    "dui": "Cause: DUI",
    "hit_and_run": "Hit-and-run",
    "covid_2020": "Year 2020 (COVID)",
    "density_1k": "Population density (+1,000 per sq mi)",
    "speed_limit_5": "Beat mean speed limit (+5 mph)",
    "income_10k": "Beat median income (+$10,000)",
}
FORMULA = (
    "y ~ C(road_user, Treatment('Driver')) + heavy_vehicle + night + weekend"
    " + unsafe_speed + dui + hit_and_run + covid_2020"
    " + density_1k + speed_limit_5 + income_10k"
)

INK = "#1f1f1e"
MUTED = "#6b6b66"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
UP = "#e34948"  # higher odds
DOWN = "#2a78d6"  # lower odds
NS = "#a3a29c"  # not significant


def road_user(people):
    on_motorcycle = people["person_veh_type"].isin(MOTORCYCLE_TYPES) | (people["veh_type"] == "MOTORCYCLE")
    role = people["person_role"]
    out = pd.Series("Other", index=people.index)
    out[role == "DRIVER"] = "Driver"
    out[role == "PASSENGER"] = "Passenger"
    out[role == "PEDESTRIAN"] = "Pedestrian"
    out[role == "BICYCLIST"] = "Bicyclist"
    out[on_motorcycle & role.isin(["DRIVER", "PASSENGER", "OTHER"])] = "Motorcyclist"
    return out


def load():
    people = pd.read_csv(
        ROOT / "dataset/participants_2016_2025_with_coordinates.csv",
        dtype={"police_beat": str, "report_id": str},
        low_memory=False,
    )
    people = people[people["year"].between(START_YEAR, END_YEAR)]

    # Crash-level flags: true if they apply to anyone in the same collision
    vc = people["violation_section"].fillna("")
    heavy = people["person_veh_type"].fillna("").str.contains(HEAVY_WORDS) | (people["veh_type"] == "TRUCK")
    flags = pd.DataFrame({
        "report_id": people["report_id"],
        "heavy_vehicle": heavy,
        "unsafe_speed": vc.str.startswith("22350"),
        "dui": vc.str.match(r"^2315[23]"),
        # hit_run_lvl is the charge level, not hit-and-run; use VC 20001/20002
        "hit_and_run": vc.str.match(r"^2000[12]"),
    }).groupby("report_id").max().astype(int)

    df = people[people["injury_known"]].copy()
    df = df.join(flags, on="report_id")
    df["y"] = df["serious_or_fatal"].astype(int)
    df["y_fatal"] = df["fatal"].astype(int)
    df["road_user"] = road_user(df)
    df["night"] = ((df["hour"] >= 20) | (df["hour"] < 6)).astype(int)
    df["weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"]).astype(int)
    df["covid_2020"] = (df["year"] == 2020).astype(int)

    beats = pd.read_csv(BEAT_FILE, dtype={"beat": str}).set_index("beat")
    df["density_1k"] = df["police_beat"].map(beats["pop_per_sq_mi"]) / 1000
    df["speed_limit_5"] = df["police_beat"].map(beats["mean_speed_limit"]) / 5
    df["income_10k"] = df["police_beat"].map(beats["median_hh_income"]) / 10000

    before = len(df)
    df = df.dropna(subset=["density_1k", "speed_limit_5", "income_10k"])
    return df, before - len(df)


def fit(df, y="y"):
    # People in the same beat share beat inputs, so cluster errors by beat
    formula = FORMULA.replace("y ~", f"{y} ~", 1)
    groups = pd.factorize(df["police_beat"])[0]
    return smf.logit(formula, data=df).fit(disp=False, cov_type="cluster", cov_kwds={"groups": groups})


def odds_table(model):
    ci = model.conf_int()
    out = pd.DataFrame({
        "odds_ratio": np.exp(model.params),
        "ci_low": np.exp(ci[0]),
        "ci_high": np.exp(ci[1]),
        "p_value": model.pvalues,
    }).drop("Intercept")
    out.index = out.index.str.replace(", Treatment('Driver')", "", regex=False)
    out.insert(0, "label", out.index.map(LABELS))
    return out.loc[list(LABELS)]


def vif_table(model):
    # Keep the intercept in X, or the VIFs come out inflated
    X = pd.DataFrame(model.model.exog, columns=model.model.exog_names)
    cols = [c for c in X.columns if c != "Intercept"]
    return pd.Series(
        [variance_inflation_factor(X.values, X.columns.get_loc(c)) for c in cols],
        index=pd.Index(cols).str.replace(", Treatment('Driver')", "", regex=False),
    ).rename(LABELS)


def plot(table, n_people, n_events):
    k = len(table)
    fig, ax = plt.subplots(figsize=(9, 7.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ypos = np.arange(k)[::-1]
    for y, (_, row) in zip(ypos, table.iterrows()):
        sig = row["p_value"] < 0.05
        color = (UP if row["odds_ratio"] > 1 else DOWN) if sig else NS
        ax.plot([row["ci_low"], row["ci_high"]], [y, y], color=color, lw=2, solid_capstyle="round")
        ax.scatter(row["odds_ratio"], y, s=64, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(1.02, y, f"{row['odds_ratio']:.2f}", transform=ax.get_yaxis_transform(),
                va="center", fontsize=9, color=INK if sig else MUTED)
    ax.axvline(1, color=MUTED, lw=1)
    ax.set_xscale("log")
    ticks = [0.125, 0.25, 0.5, 1, 2, 4, 8]
    ax.set_xticks(ticks, [f"{t:g}×" for t in ticks])
    ax.set_xlim(0.1, 14)
    ax.minorticks_off()
    ax.set_yticks(ypos, table["label"], fontsize=9.5, color=INK)
    ax.tick_params(length=0, colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", labelcolor=INK)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Odds ratio (log scale) — right of 1× means higher chance of serious/fatal injury",
                  color=MUTED, fontsize=9)
    ax.set_title(
        "What raises the odds of a serious or fatal injury?\n"
        f"Logistic regression, San Diego 2018–2025, {n_people:,} injured people ({n_events:,} serious/fatal)\n"
        "Gray = not significant (p ≥ .05)",
        fontsize=11, color=INK, loc="left", pad=14,
    )
    fig.savefig(HERE / "odds_ratios.png", dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


def main():
    df, dropped = load()
    model = fit(df)
    table = odds_table(model)
    table.round(4).to_csv(HERE / "odds_ratios.csv")
    plot(table, len(df), int(df["y"].sum()))

    auc = roc_auc_score(df["y"], model.predict(df))
    vif = vif_table(model)
    fatal = odds_table(fit(df, "y_fatal"))
    lines = [
        f"People: {len(df):,} (dropped {dropped} with no beat match)",
        f"Serious/fatal: {int(df['y'].sum()):,} ({df['y'].mean():.1%})",
        f"Fatal: {int(df['y_fatal'].sum()):,}",
        "",
        "Road-user counts:",
        df["road_user"].value_counts().to_string(),
        "",
        "Serious/fatal rate by road user (raw, before adjusting):",
        df.groupby("road_user")["y"].mean().round(4).to_string(),
        "",
        f"AUC (0.5 = coin flip, 1 = perfect): {auc:.3f}",
        f"McFadden pseudo R-squared: {model.prsquared:.3f}",
        "",
        "Variance inflation factors (above 5 means inputs overlap too much):",
        vif.round(2).to_string(),
        "",
        "Main model: odds ratios",
        table.round(3).to_string(),
        "",
        "Check: same model with Y = fatal only",
        fatal.round(3).to_string(),
        "",
        str(model.summary()),
    ]
    (HERE / "model_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:30]))
    print(table.round(3).to_string())
    print("\nFatal-only:")
    print(fatal.round(3).to_string())


if __name__ == "__main__":
    main()
