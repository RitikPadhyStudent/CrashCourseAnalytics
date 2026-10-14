# Data notes

Problems found in the data during the correlation and regression work, and how they are handled. Check these before using the same fields in the report, the slides or a dashboard.

## `hit_run_lvl` is not hit-and-run

`hit_run_lvl` holds the **charge level** of the cited violation (MISDEMEANOR or FELONY), not whether the crash was a hit-and-run.

- **How we know:** 45% of collisions are MISDEMEANOR, but only 11% of those carry a hit-and-run Vehicle Code section.
- **What to use instead:** violation section 20001 (hit-and-run with injury) or 20002 (hit-and-run with property damage).
- **Where it is fixed:** the correlation and regression use the violation section.
- **Still to check:** any chart or text that treats `hit_run_lvl` as hit-and-run.

## Police-beat numbers clash with county beats

The City of San Diego beat file contains SDPD beats (`div` 1–9) and county sheriff beats (`div` 0). The two reuse the same numbers: 821 is both Rolando (SDPD) and Santa Ysabel (county).

- **Our collisions are all SDPD,** so each beat number must use the SDPD polygon.
- **`dataset/spatial/police_beats_*_analysis.geojson` has the wrong polygons.** It used the county polygon for 83 of the 125 SDPD beats, up to 57 miles from the real beat.
- **Website map, fixed:** `website/data/police_beats_web.geojson` is now built by `scripts/build_police_beats_web.py` from SDPD beats only.
- **Correlation, correct:** it uses SDPD beats only.
- **Still to fix:** `dataset/spatial/` and any ArcGIS maps built from it.

## Blank injury levels

About 72% of participants have no injury level recorded. There is no "no injury" code, so a blank most likely means the person was not hurt. Injury rates in the analysis therefore mean "how severe, given that someone was hurt."

## What the data does not have

The records have no age or sex for the people involved, though both strongly affect how badly people are hurt. Mention this as a limitation in the report.
