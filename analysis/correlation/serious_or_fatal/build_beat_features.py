"""Build one row per SDPD police beat with Y and every input variable.

Y = serious_fatal_rate: participants with a serious, severe or fatal
injury divided by participants with a known injury level, 2018-2025.

Inputs come from the collision data itself (what kind of crashes happen
in the beat) and from external sources (who lives there, what the
streets are like). See README.md for the full variable list.

Run download_external_data.py first. Usage (from the repo root):
  python3 analysis/correlation/serious_or_fatal/build_beat_features.py
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
RAW = HERE / "data" / "raw"
OUT_FILE = HERE / "beat_features.csv"

START_YEAR = 2018  # 2016 is incomplete and 2017 has only 366 rows
END_YEAR = 2025
MIN_KNOWN_INJURY = 50  # beats with fewer known-injury records get no Y

FEET_CRS = "EPSG:2230"  # California State Plane zone 6, US feet
SQFT_PER_SQMI = 5280 ** 2

# SANDAG FUNCLASS codes
FREEWAY_CLASSES = {"F", "1", "R"}  # freeway, freeway ramp, on/off ramp
ARTERIAL_CLASSES = {"4", "6", "D", "S", "E"}  # major, prime, six-lane, expressway
NOT_A_STREET = {"P", "M", "U", "W", "B", "T"}  # paper, military, unpaved, paths

COMMERCIAL_ZONES = ("CC", "CN", "CO", "CR", "CV", "CP")
INDUSTRIAL_ZONES = ("IL", "IH", "IP", "IS", "IBT")
MOTORCYCLE_TYPES = {"Motorcycle", "Motor Driven Cycle/Scooter"}
HEAVY_WORDS = "Truck|Semi|Bus|Tractor|Trailer"


def load_beats():
    # The city file also holds county sheriff beats (div 0) that reuse SDPD
    # beat numbers, e.g. 821 is both Rolando (SDPD) and Santa Ysabel (county).
    # Keep SDPD only, and merge beats split into several polygons.
    beats = gpd.read_file(RAW / "pd_beats_datasd.geojson")
    beats = beats[beats["div"].astype(int) > 0]
    beats["beat"] = beats["beat"].astype(int).astype(str)
    beats = beats.dissolve(by="beat", aggfunc={"name": "first"}).reset_index()
    beats = beats[["beat", "name", "geometry"]].to_crs(FEET_CRS)
    beats["area_sq_mi"] = beats.area / SQFT_PER_SQMI
    return beats.reset_index(drop=True)


def share(mask, groups):
    return mask.groupby(groups).mean()


def collision_features():
    """Y plus the crash-mix variables, from the project's own data."""
    people = pd.read_csv(
        ROOT / "dataset/participants_2016_2025_with_coordinates.csv",
        dtype={"police_beat": str, "report_id": str},
        low_memory=False,
    )
    people = people[people["year"].between(START_YEAR, END_YEAR)]
    crashes = pd.read_csv(
        ROOT / "dataset/collisions_2016_2025_with_coordinates.csv",
        dtype={"police_beat": str, "report_id": str},
        low_memory=False,
    )
    crashes = crashes[crashes["year"].between(START_YEAR, END_YEAR)]

    pb = people["police_beat"]
    known = people[people["injury_known"]]
    out = pd.DataFrame({
        "known_injury_records": known.groupby("police_beat").size(),
        "serious_fatal_records": known.groupby("police_beat")["serious_or_fatal"].sum(),
    })
    out["serious_fatal_rate"] = out["serious_fatal_records"] / out["known_injury_records"]

    # Who is involved (share of all participants)
    role = people["person_role"]
    out["pct_pedestrian"] = share(role == "PEDESTRIAN", pb)
    out["pct_bicyclist"] = share(role == "BICYCLIST", pb)
    out["pct_motorcyclist"] = share(
        people["person_veh_type"].isin(MOTORCYCLE_TYPES) | (people["veh_type"] == "MOTORCYCLE"), pb
    )
    out["pct_heavy_vehicle"] = share(
        people["person_veh_type"].fillna("").str.contains(HEAVY_WORDS) | (people["veh_type"] == "TRUCK"), pb
    )
    out["pct_injury_known"] = share(people["injury_known"], pb)

    # What kind of crashes (share of collisions)
    cb = crashes["police_beat"]
    n_years = END_YEAR - START_YEAR + 1
    out["collisions_per_year"] = crashes.groupby("police_beat").size() / n_years
    out["persons_per_collision"] = crashes.groupby("police_beat")["participant_records"].mean()
    hour = crashes["hour"]
    out["pct_night"] = share((hour >= 20) | (hour < 6), cb)
    out["pct_weekend"] = share(crashes["day_of_week"].isin(["Saturday", "Sunday"]), cb)
    out["pct_possible_freeway"] = share(crashes["possible_freeway"], cb)
    # hit_run_lvl is the charge level (misdemeanor/felony), not hit-and-run,
    # so hit-and-run comes from the Vehicle Code section (20001 / 20002)
    vc = crashes["violation_section"].fillna("")
    out["pct_hit_and_run"] = share(vc.str.match(r"^2000[12]"), cb)
    out["pct_unsafe_speed"] = share(vc.str.startswith("22350"), cb)
    out["pct_dui"] = share(vc.str.match(r"^2315[23]"), cb)
    out["pct_red_light"] = share(vc.str.startswith("21453"), cb)
    out["pct_ped_right_of_way"] = share(vc.str.match(r"^2195[04]"), cb)
    out["pct_unsafe_turn"] = share(vc.str.match(r"^(22107|38314)"), cb)
    return out


def road_features(beats):
    """Street network, from SANDAG Roads_All (segments carry their beat)."""
    roads = pd.read_csv(RAW / "Roads_All.csv", encoding="utf-8-sig", low_memory=False)
    roads = roads[~roads["FUNCLASS"].isin(NOT_A_STREET)]
    # A segment on a beat boundary gives half its length to each side
    sides = []
    for side in ("L_BEAT", "R_BEAT"):
        part = roads[["LENGTH", "SPEED", "FUNCLASS", "ONEWAY", "FNODE", "TNODE", side]].copy()
        part["beat"] = part.pop(side)
        part["miles"] = part["LENGTH"] / 5280 / 2
        sides.append(part)
    segs = pd.concat(sides).dropna(subset=["beat"])
    segs["beat"] = segs["beat"].astype(int).astype(str)

    freeway = segs["FUNCLASS"].isin(FREEWAY_CLASSES)
    streets = segs[~freeway]
    g = streets.groupby("beat")
    out = pd.DataFrame({"street_miles": g["miles"].sum()})
    out["freeway_miles"] = segs[freeway].groupby("beat")["miles"].sum()
    out["freeway_miles"] = out["freeway_miles"].fillna(0)
    out["pct_arterial"] = (
        streets[streets["FUNCLASS"].isin(ARTERIAL_CLASSES)].groupby("beat")["miles"].sum()
        / out["street_miles"]
    ).fillna(0)
    out["pct_one_way"] = (
        streets[streets["ONEWAY"].isin(["F", "T"])].groupby("beat")["miles"].sum() / out["street_miles"]
    ).fillna(0)
    posted = streets[streets["SPEED"] > 0]
    out["mean_speed_limit"] = (
        (posted["SPEED"] * posted["miles"]).groupby(posted["beat"]).sum()
        / posted.groupby("beat")["miles"].sum()
    )
    out["pct_40mph_plus"] = (
        posted[posted["SPEED"] >= 40].groupby("beat")["miles"].sum() / posted.groupby("beat")["miles"].sum()
    ).fillna(0)

    # Intersections: street nodes where 3 or more segments meet
    one_side = roads[~roads["FUNCLASS"].isin(FREEWAY_CLASSES)].dropna(subset=["L_BEAT"])
    nodes = pd.concat([
        one_side[["FNODE", "L_BEAT"]].rename(columns={"FNODE": "node"}),
        one_side[["TNODE", "L_BEAT"]].rename(columns={"TNODE": "node"}),
    ])
    degree = nodes.groupby("node").agg(n=("L_BEAT", "size"), beat=("L_BEAT", "first"))
    inter = degree[degree["n"] >= 3]
    out["intersections"] = inter.groupby(inter["beat"].astype(int).astype(str)).size()

    out = out.reindex(beats["beat"])
    area = beats.set_index("beat")["area_sq_mi"]
    out["street_miles_per_sq_mi"] = out["street_miles"] / area
    out["intersections_per_sq_mi"] = out["intersections"].fillna(0) / area
    return out


def points_in_beats(df, lon, lat, beats):
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs="EPSG:4326")
    return gpd.sjoin(pts.to_crs(FEET_CRS), beats[["beat", "geometry"]], predicate="within")


def lines_in_beats(path, beats):
    lines = gpd.read_file(path).to_crs(FEET_CRS)
    pieces = gpd.overlay(lines, beats[["beat", "geometry"]], how="intersection", keep_geom_type=True)
    return (pieces.length / 5280).groupby(pieces["beat"]).sum()


def place_features(beats, streets):
    """Bike lanes, transit, traffic volume, parking meters, zoning."""
    out = pd.DataFrame(index=beats["beat"])
    area = beats.set_index("beat")["area_sq_mi"]

    bike = lines_in_beats(RAW / "Bikeways.geojson", beats)
    out["bikeway_miles_per_street_mile"] = bike.reindex(out.index).fillna(0) / streets["street_miles"]

    stops = pd.read_csv(RAW / "Transit_Stops_GTFS.csv", encoding="utf-8-sig")
    stops = stops[stops["location_type"] != 1]  # drop parent stations
    stops = points_in_beats(stops, "stop_lon", "stop_lat", beats)
    out["transit_stops_per_sq_mi"] = stops.groupby("beat").size().reindex(out.index).fillna(0) / area

    meters = pd.read_csv(RAW / "parking_meters.csv")
    meters = meters[meters["latitude"].between(32, 34)]
    meters = points_in_beats(meters, "longitude", "latitude", beats)
    out["parking_meters_per_sq_mi"] = meters.groupby("beat").size().reindex(out.index).fillna(0) / area

    counts = pd.read_csv(RAW / "traffic_counts.csv").dropna(subset=["lat", "lng", "adt_total"])
    counts = points_in_beats(counts, "lng", "lat", beats)
    out["median_daily_traffic"] = counts.groupby("beat")["adt_total"].median()

    zoning = gpd.read_file(RAW / "Zoning_Base_SD.geojson").to_crs(FEET_CRS)
    pieces = gpd.overlay(zoning, beats[["beat", "geometry"]], how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.area
    zoned = pieces.groupby("beat")["area"].sum()
    for label, prefixes in (("commercial", COMMERCIAL_ZONES), ("industrial", INDUSTRIAL_ZONES)):
        hit = pieces["ZONE_NAME"].str.extract(r"^([A-Z]+)")[0].isin(prefixes)
        out[f"pct_{label}_zoning"] = (pieces[hit].groupby("beat")["area"].sum() / zoned).reindex(out.index).fillna(0)
    return out


def census_features(beats):
    """ACS 5-year tract estimates, split into beats by share of tract area."""
    acs = json.loads((RAW / "acs_tracts.json").read_text())
    rows = {}
    for geo, tables in acs["data"].items():
        est = {}
        for t in tables.values():
            est.update(t["estimate"])
        rows[geo.replace("14000US", "")] = est
    acs_df = pd.DataFrame.from_dict(rows, orient="index")

    e = acs_df
    tract = pd.DataFrame(index=acs_df.index)
    tract["pop"] = e["B01003001"]
    tract["poverty_universe"] = e["B17001001"]
    tract["poverty"] = e["B17001002"]
    tract["households"] = e["B25044001"]
    tract["zero_vehicle"] = e["B25044003"] + e["B25044010"]
    tract["workers"] = e["B08301001"]
    tract["transit"] = e["B08301010"]
    tract["bike"] = e["B08301018"]
    tract["walk"] = e["B08301019"]
    tract["wfh"] = e["B08301021"]
    tract["age_65_plus"] = e[[f"B01001{i:03d}" for i in [*range(20, 26), *range(44, 50)]]].sum(axis=1)
    tract["under_18"] = e[[f"B01001{i:03d}" for i in [*range(3, 7), *range(27, 31)]]].sum(axis=1)
    tract["hispanic"] = e["B03002012"]
    # Medians cannot be summed; carry income x population for a weighted mean
    tract["income_x_pop"] = e["B19013001"] * tract["pop"]
    tract["pop_with_income"] = tract["pop"].where(e["B19013001"].notna(), 0)
    tract = tract.fillna(0)

    shapes = gpd.read_file(f"zip://{RAW / 'tl_2023_06_tract.zip'}")
    shapes = shapes[shapes["COUNTYFP"] == "073"].to_crs(FEET_CRS)
    shapes["tract_area"] = shapes.area
    pieces = gpd.overlay(shapes[["GEOID", "tract_area", "geometry"]], beats[["beat", "geometry"]], how="intersection")
    w = pieces.area / pieces["tract_area"]
    vals = tract.reindex(pieces["GEOID"]).to_numpy() * w.to_numpy()[:, None]
    by_beat = pd.DataFrame(vals, columns=tract.columns).groupby(pieces["beat"].to_numpy()).sum()

    area = beats.set_index("beat")["area_sq_mi"]
    b = by_beat.reindex(beats["beat"])
    out = pd.DataFrame(index=beats["beat"])
    out["population"] = b["pop"]
    out["pop_per_sq_mi"] = b["pop"] / area
    out["median_hh_income"] = b["income_x_pop"] / b["pop_with_income"].replace(0, np.nan)
    out["pct_poverty"] = b["poverty"] / b["poverty_universe"]
    out["pct_zero_vehicle_hh"] = b["zero_vehicle"] / b["households"]
    out["pct_walk_to_work"] = b["walk"] / b["workers"]
    out["pct_bike_to_work"] = b["bike"] / b["workers"]
    out["pct_transit_to_work"] = b["transit"] / b["workers"]
    out["pct_work_from_home"] = b["wfh"] / b["workers"]
    out["pct_age_65_plus"] = b["age_65_plus"] / b["pop"]
    out["pct_under_18"] = b["under_18"] / b["pop"]
    out["pct_hispanic"] = b["hispanic"] / b["pop"]
    return out, acs["release"]["name"]


def crime_features(population):
    """SDPD NIBRS offenses, yearly average 2020-2025, per 1,000 residents."""
    frames = []
    for path in sorted(RAW.glob("nibrs_*.csv")):
        df = pd.read_csv(path, usecols=["beat", "violent_crime", "ibr_offense_description"], dtype={"beat": str})
        frames.append(df)
    crime = pd.concat(frames)
    crime["beat"] = crime["beat"].str.replace(r"\.0$", "", regex=True)
    n_years = len(frames)
    g = crime.groupby("beat")
    per_1k = 1000 / population.where(population >= 1000)  # unstable below 1,000 residents
    out = pd.DataFrame(index=population.index)
    out["violent_crime_per_1k"] = g["violent_crime"].sum().reindex(out.index) / n_years * per_1k
    dui = crime["ibr_offense_description"] == "Driving Under the Influence"
    out["dui_arrests_per_1k"] = crime[dui].groupby("beat").size().reindex(out.index) / n_years * per_1k
    return out


def main():
    beats = load_beats()
    print(f"City police beats: {len(beats)}")

    crash = collision_features().reindex(beats["beat"])
    streets = road_features(beats)
    places = place_features(beats, streets)
    census, release = census_features(beats)
    crime = crime_features(census["population"])
    print(f"Census: {release}")

    table = pd.concat([crash, streets, places, census, crime], axis=1)
    table.insert(0, "name", beats.set_index("beat")["name"])
    table.insert(1, "area_sq_mi", beats.set_index("beat")["area_sq_mi"])
    table["collisions_per_street_mile"] = table["collisions_per_year"] / table["street_miles"]
    table["in_analysis"] = table["known_injury_records"] >= MIN_KNOWN_INJURY
    table.index.name = "beat"
    table.round(5).to_csv(OUT_FILE)
    print(f"Beats with Y (>= {MIN_KNOWN_INJURY} known-injury records): {table['in_analysis'].sum()}")
    print(f"Wrote {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
