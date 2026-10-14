"""Export the regression and correlation results as JSON for the website.

Reads the analysis scripts and their outputs (it changes none of them) and
writes two small files for the interactive charts:
  website/data/regression.json    odds ratios for both models
  website/data/correlation.json   Spearman matrix, p-values, and the beat values

Run the correlation and regression steps first. Usage (from the repo root):
  python3 analysis/export_website_data.py
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "website" / "data"
REG_DIR = ROOT / "analysis/regression/serious_or_fatal"
COR_DIR = ROOT / "analysis/correlation/serious_or_fatal"


def import_script(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Regression terms -> (short key, group, plain-language name for sentences)
TERMS = {
    "C(road_user)[T.Pedestrian]": ("pedestrian", "Who was hurt", "Pedestrians"),
    "C(road_user)[T.Motorcyclist]": ("motorcyclist", "Who was hurt", "Motorcyclists"),
    "C(road_user)[T.Bicyclist]": ("bicyclist", "Who was hurt", "Bicyclists"),
    "C(road_user)[T.Passenger]": ("passenger", "Who was hurt", "Passengers"),
    "C(road_user)[T.Other]": ("other_user", "Who was hurt", "Other road users"),
    "heavy_vehicle": ("heavy_vehicle", "The crash", "Crashes involving a truck or bus"),
    "night": ("night", "The crash", "Crashes at night (8pm–6am)"),
    "weekend": ("weekend", "The crash", "Weekend crashes"),
    "unsafe_speed": ("unsafe_speed", "The crash", "Crashes caused by unsafe speed"),
    "dui": ("dui", "The crash", "Crashes caused by DUI"),
    "hit_and_run": ("hit_and_run", "The crash", "Hit-and-run crashes"),
    "covid_2020": ("covid_2020", "The crash", "Crashes in 2020 (COVID)"),
    "density_1k": ("density", "The place", "Each extra 1,000 residents per sq mi"),
    "speed_limit_5": ("speed_limit", "The place", "Each extra 5 mph of average speed limit"),
    "income_10k": ("income", "The place", "Each extra $10,000 of median income"),
}
COMPARED_WITH = {
    "Who was hurt": "drivers",
    "The crash": "otherwise similar crashes",
    "The place": "otherwise similar crashes",
}
NOTES = {
    "hit_and_run": (
        "Not a sign that fleeing is safer: 88% of these cases carry the property-damage "
        "hit-and-run code, so they are mostly low-harm crashes by how they were recorded."
    ),
    "unsafe_speed": (
        "VC 22350 means 'too fast for conditions'. Officers often use it for rear-end "
        "crashes in slow traffic, so it is not the same as high speed."
    ),
    "other_user": "Only 261 people are in this group, so the estimate is very uncertain.",
}


def regression():
    reg = import_script(REG_DIR / "logistic_regression.py")
    df, _ = reg.load()
    models = {}
    for key, y in (("serious_or_fatal", "y"), ("fatal", "y_fatal")):
        model = reg.fit(df, y)
        table = reg.odds_table(model)
        rows = []
        for term, row in table.iterrows():
            short, group, name = TERMS[term]
            rows.append({
                "key": short,
                "label": row["label"],
                "group": group,
                "name": name,
                "compared_with": COMPARED_WITH[group],
                "odds_ratio": round(row["odds_ratio"], 4),
                "ci_low": round(row["ci_low"], 4),
                "ci_high": round(row["ci_high"], 4),
                "p_value": round(row["p_value"], 6),
                "note": NOTES.get(short),
            })
        models[key] = {
            "outcome": "serious or fatal injury" if key == "serious_or_fatal" else "fatal injury",
            "events": int(df[y].sum()),
            "auc": round(roc_auc_score(df[y], model.predict(df)), 3),
            "rows": rows,
        }
    raw = df.groupby("road_user")["y"].agg(["size", "mean"])
    return {
        "people": len(df),
        "years": f"{reg.START_YEAR}–{reg.END_YEAR}",
        "raw_rates": {k: {"people": int(v["size"]), "rate": round(v["mean"], 4)} for k, v in raw.iterrows()},
        "models": models,
    }


OUR_GROUPS = {"Outcome", "Who is involved", "When and why"}


def correlation():
    cor = import_script(COR_DIR / "correlation_heatmap.py")
    table = pd.read_csv(COR_DIR / "beat_features.csv", dtype={"beat": str})
    table = table[table["in_analysis"]]
    cols = list(cor.LABELS)
    data = table[cols]

    k = len(cols)
    rho = np.full((k, k), np.nan)
    p = np.full((k, k), np.nan)
    n = np.zeros((k, k), dtype=int)
    for i in range(k):
        for j in range(i + 1):
            pair = data[[cols[i], cols[j]]].dropna()
            n[i, j] = n[j, i] = len(pair)
            if i == j:
                rho[i, j], p[i, j] = 1.0, 0.0
                continue
            r, pv = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
            rho[i, j] = rho[j, i] = r
            p[i, j] = p[j, i] = pv

    variables = []
    for group, members in cor.GROUPS.items():
        for col, label in members.items():
            source = "Our collision data" if group in OUR_GROUPS else "Outside data"
            if col == "collisions_per_street_mile":
                source = "Our collision data + SANDAG roads"
            variables.append({"key": col, "label": label, "group": group, "source": source})

    beats = [
        {"beat": b, "name": str(name).title(), "values": [None if pd.isna(v) else round(float(v), 6) for v in vals]}
        for b, name, vals in zip(table["beat"], table["name"], data.to_numpy())
    ]
    return {
        "y": cor.Y,
        "n_beats": len(table),
        "variables": variables,
        "rho": np.round(rho, 4).tolist(),
        "p": [[float(f"{x:.3g}") for x in row] for row in p],
        "n": n.tolist(),
        "beats": beats,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in (("regression.json", regression), ("correlation.json", correlation)):
        path = OUT / name
        path.write_text(json.dumps(build(), separators=(",", ":"), ensure_ascii=False))
        print(f"Wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
