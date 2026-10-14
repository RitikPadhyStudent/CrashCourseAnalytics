"""Download the external datasets used to describe each police beat.

Files go to data/raw/ (git-ignored, about 400 MB). Files that already
exist are skipped, so the script is safe to re-run.

Usage (from the repo root):
  python3 analysis/correlation/serious_or_fatal/download_external_data.py
"""

import json
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"

SANDAG = "https://geo.sandag.org/server/rest/directories/downloads"
DATASD = "https://seshat.datasd.org"

FILES = {
    # City of San Diego police beat boundaries
    "pd_beats_datasd.geojson": f"{DATASD}/gis_police_beats/pd_beats_datasd.geojson",
    # SANDAG / SanGIS road centerlines: speed limit, functional class, beat
    "Roads_All.csv": f"{SANDAG}/Roads_All.csv",
    # SANDAG bikeways (bike lanes, routes, paths, separated bikeways)
    "Bikeways.geojson": f"{SANDAG}/Bikeways.geojson",
    # Transit stops from the MTS / NCTD GTFS feeds
    "Transit_Stops_GTFS.csv": f"{SANDAG}/Transit_Stops_GTFS.csv",
    # City of San Diego base zoning
    "Zoning_Base_SD.geojson": f"{SANDAG}/Zoning_Base_SD.geojson",
    # City of San Diego traffic volume (ADT) counts
    "traffic_counts.csv": f"{DATASD}/traffic_adt_counts/traffic_counts_datasd.csv",
    # City of San Diego parking meter locations
    "parking_meters.csv": f"{DATASD}/parking_meters_locations/parking_meters_current.csv",
    # Census 2023 tract boundaries for California
    "tl_2023_06_tract.zip": "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_06_tract.zip",
}
for year in range(2020, 2026):
    # SDPD crime offenses (NIBRS), one file per year
    FILES[f"nibrs_{year}.csv"] = f"{DATASD}/police_nibrs/pd_nibrs_{year}_datasd.csv"

# American Community Survey 5-year tables, via the Census Reporter API
# (the official Census API now needs a key)
ACS_TABLES = ["B01003", "B19013", "B17001", "B25044", "B08301", "B01001", "B03002"]
ACS_URL = "https://api.censusreporter.org/1.0/data/show/latest"
SD_COUNTY_TRACTS = "140|05000US06073"
# Census Reporter rejects the default python-requests user agent
HEADERS = {"User-Agent": "Mozilla/5.0 (CrashCourseAnalytics student project)"}


def download(url, path):
    print(f"Downloading {path.name}")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        path = RAW / name
        if not path.exists():
            download(url, path)

    path = RAW / "acs_tracts.json"
    if not path.exists():
        print("Downloading ACS tract tables")
        merged = {}
        for table in ACS_TABLES:
            r = requests.get(
                ACS_URL,
                params={"table_ids": table, "geo_ids": SD_COUNTY_TRACTS},
                timeout=300,
                headers=HEADERS,
            )
            r.raise_for_status()
            payload = r.json()
            merged.setdefault("release", payload.get("release"))
            for geo, tables in payload["data"].items():
                merged.setdefault("data", {}).setdefault(geo, {}).update(tables)
        path.write_text(json.dumps(merged))

    print("All files in", RAW)


if __name__ == "__main__":
    main()
