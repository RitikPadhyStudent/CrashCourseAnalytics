"""Rebuild the beat map's boundaries with San Diego Police Department beats only.

The City of San Diego beat file also holds county sheriff beats (div 0) that
reuse SDPD beat numbers. 821, for example, is both Rolando (SDPD) and Santa
Ysabel (county). Our collisions are all SDPD, so the map must use the SDPD
polygon for each number. This keeps the 125 SDPD beats, merges beats split
into several pieces, and simplifies the outlines for the web.

Input:  analysis/correlation/serious_or_fatal/data/raw/pd_beats_datasd.geojson
        (run analysis/correlation/serious_or_fatal/download_external_data.py)
Output: website/data/police_beats_web.geojson

Usage (from the repo root):
  python3 scripts/build_police_beats_web.py
"""

import json
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "analysis/correlation/serious_or_fatal/data/raw/pd_beats_datasd.geojson"
OUT_FILE = ROOT / "website/data/police_beats_web.geojson"

SIMPLIFY_FEET = 40  # outline detail kept; small enough to be invisible on the map


def round_coords(coords, digits=5):
    if isinstance(coords[0], (int, float)):
        return [round(c, digits) for c in coords]
    return [round_coords(c, digits) for c in coords]


def main():
    beats = gpd.read_file(SOURCE)
    beats = beats[beats["div"].astype(int) > 0]  # div 0 = county sheriff beats
    beats["police_beat"] = beats["beat"].astype(int)
    beats = beats[["police_beat", "geometry"]].dissolve(by="police_beat").reset_index()

    beats = beats.to_crs("EPSG:2230")
    beats["geometry"] = beats.simplify(SIMPLIFY_FEET, preserve_topology=True)
    beats = beats.to_crs("EPSG:4326").sort_values("police_beat")

    features = []
    for beat, geom in zip(beats["police_beat"], beats.geometry):
        shape = geom.__geo_interface__
        if shape["type"] == "Polygon":
            shape = {"type": "MultiPolygon", "coordinates": [shape["coordinates"]]}
        shape["coordinates"] = round_coords(shape["coordinates"])
        features.append({"type": "Feature", "properties": {"police_beat": int(beat)}, "geometry": shape})

    OUT_FILE.write_text(json.dumps({
        "type": "FeatureCollection",
        "name": "police_beats_web",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }, separators=(",", ":")))
    print(f"Wrote {len(features)} SDPD beats to {OUT_FILE.relative_to(ROOT)} ({OUT_FILE.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
