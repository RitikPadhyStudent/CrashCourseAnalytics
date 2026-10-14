# Correlation: serious/fatal injury rate by police beat

**Question:** Which characteristics of a police beat go along with a higher share of serious or fatal injuries?

- **Unit:** one SDPD police beat. There are 125 city beats. The 112 beats with at least 50 known-injury records from 2018 to 2025 are used.
- **Y:** `serious_fatal_rate`, the number of participants with a serious, severe or fatal injury divided by the number of participants with a known injury level, 2018–2025.
- **Method:** Spearman rank correlation, because many inputs are skewed (density, parking meters, crime). Pearson r is also given in `correlations_with_y.csv`.

## Run it

From the repo root (needs Python 3.9+ and `analysis/requirements.txt`):

```
pip install -r analysis/requirements.txt
python3 analysis/correlation/serious_or_fatal/download_external_data.py   # ~400 MB into data/raw/ (git-ignored)
python3 analysis/correlation/serious_or_fatal/build_beat_features.py      # -> beat_features.csv
python3 analysis/correlation/serious_or_fatal/correlation_heatmap.py      # -> heatmaps and CSVs
```

## Outputs

| File | What it is |
|------|------------|
| `beat_features.csv` | One row per beat: Y, its numerator and denominator, every input, and `in_analysis` |
| `correlation_heatmap.png` | Full Spearman matrix, with Y in the first row and column |
| `y_correlations.png` | Only the correlations with Y, sorted, with significance stars |
| `correlation_matrix.csv` | The full matrix as numbers |
| `correlations_with_y.csv` | Spearman and Pearson r with Y, p-values and n |

## Input variables

### From our collision data (2018–2025)

| Variable | Definition |
|----------|------------|
| `pct_pedestrian`, `pct_bicyclist` | Share of participants with that `person_role` |
| `pct_motorcyclist` | Share of participants on a motorcycle or motor-driven cycle/scooter |
| `pct_heavy_vehicle` | Share of participants in a truck, semi, bus or tractor |
| `persons_per_collision` | Mean participants per collision |
| `pct_injury_known` | Share of participants with a known injury level (a reporting check) |
| `collisions_per_year` | Unique collisions per year |
| `collisions_per_street_mile` | Collisions per year per mile of city street |
| `pct_night` | Share of collisions from 8pm to 6am |
| `pct_weekend` | Share of collisions on Saturday or Sunday |
| `pct_possible_freeway` | Share flagged `possible_freeway` |
| `pct_hit_and_run` | Share with Vehicle Code 20001 or 20002 |
| `pct_unsafe_speed` | VC 22350 |
| `pct_dui` | VC 23152 or 23153 |
| `pct_red_light` | VC 21453 |
| `pct_ped_right_of_way` | VC 21950 or 21954 |
| `pct_unsafe_turn` | VC 22107 or 38314 |

### External sources

| Variable | Source | Definition |
|----------|--------|------------|
| Beat boundaries, `area_sq_mi` | [City of San Diego police beats](https://data.sandiego.gov/datasets/gis-police-beats/) | SDPD beats only (`div` > 0) |
| `mean_speed_limit`, `pct_40mph_plus`, `pct_arterial`, `pct_one_way`, `street_miles_per_sq_mi`, `intersections_per_sq_mi`, `freeway_miles` | [SANDAG Roads_All](https://data.sandiego.gov/datasets/gis-roads-all/) | City streets only, with freeways and ramps counted separately. Lengths are weighted, and each segment carries its own beat. An intersection is a node where 3 or more segments meet. |
| `median_daily_traffic` | [City traffic volume counts](https://data.sandiego.gov/datasets/traffic-adt-counts/) | Median 24-hour count at the count stations in the beat (2023 onward, 5 beats have none) |
| `bikeway_miles_per_street_mile` | [SANDAG bikeways](https://data.sandiego.gov/datasets/gis-bike-routes/) | All classes: lanes, routes, paths and separated bikeways |
| `transit_stops_per_sq_mi` | [SANDAG transit stops (GTFS)](https://data.sandiego.gov/datasets/gis-transit-stops/) | MTS and NCTD stops, not counting parent stations |
| `parking_meters_per_sq_mi` | [City parking meter locations](https://data.sandiego.gov/datasets/parking-meters-locations/) | A proxy for busy commercial streets |
| `pct_commercial_zoning`, `pct_industrial_zoning` | [City base zoning](https://data.sandiego.gov/datasets/gis-zoning/) | Share of zoned area in CC/CN/CO/CR/CV/CP or IL/IH/IP/IS/IBT zones |
| `pop_per_sq_mi`, `median_hh_income`, `pct_poverty`, `pct_zero_vehicle_hh`, `pct_walk_to_work`, `pct_bike_to_work`, `pct_transit_to_work`, `pct_work_from_home`, `pct_age_65_plus`, `pct_under_18`, `pct_hispanic` | [ACS 2024 5-year](https://censusreporter.org) tracts plus [TIGER 2023 tract boundaries](https://www2.census.gov/geo/tiger/TIGER2023/TRACT/) | Tract counts are split into beats by share of tract area. Income is a population-weighted mean of the tract medians. |
| `violent_crime_per_1k`, `dui_arrests_per_1k` | [SDPD NIBRS offenses](https://data.sandiego.gov/datasets/police-nibrs/) 2020–2025 | Yearly average per 1,000 residents. Left blank for beats with under 1,000 residents. |

## Caveats

- **Ecological:** these are correlations between beats, not between people. A beat with a high share of pedestrians does not tell you whether pedestrians there get hurt more.
- **What Y means:** blank injury levels (72% of participants) most likely mean no injury, so Y is "how severe, given someone was hurt."
- **`hit_run_lvl` is not hit-and-run.** It holds the charge level: 45% of collisions are MISDEMEANOR, but only 11% of those carry a hit-and-run section. Hit-and-run here comes from the Vehicle Code section instead.
- **Beat numbers clash:** the city beat file also contains county sheriff beats that reuse SDPD numbers (821 is both Rolando and Santa Ysabel). This analysis keeps SDPD beats only. `dataset/spatial/police_beats_*_analysis.geojson` has the county polygon instead of the SDPD one for 83 of the 125 SDPD beats. See `documentation/data_notes.md`.
- **Zoning:** downtown and the other planned districts (CCPD and similar) count as neither commercial nor industrial.
- **Inputs are related to each other:** density, transit, intersections, beat area and income move together, as the heatmap shows. Check this before putting them in one regression.
