# Data Cleaning

- **Script:** `scripts/clean_data.py`
- **Input:** `dataset/sd_county_collision_data.csv`
- **Output:** `dataset/sd_county_collision_data_clean.csv`

Run from the repo root:

```
python3 scripts/clean_data.py
```

## Cleaned

| Step | Result |
|------|--------|
| Stripped extra spaces from all values | 626,739 values fixed |
| Removed completely blank rows | 0 found |
| Removed exact duplicate rows | 5,979 rows removed |
| Kept 2015–2025 only | 11,479 rows removed |
| Fixed typo `VISABLE` → `VISIBLE` in `person_injury_lvl` | 11,467 values fixed |

## Before vs after

| | Before | After |
|---|---|---|
| Rows (people) | 163,334 | 145,876 |
| Collisions | 77,414 | 72,242 |
| Years | 2015–2026 | 2015–2025 |

## Left as is (by choice)

- Blank values, including blank injury levels (73% of rows)
- Sparse years: 2015 (9 rows), 2016 (6,338 rows), 2017 (368 rows)
- Suspicious times such as `00:00` and `00:01`
- Column names and data types

## Not done yet (possible later)

- Group injury levels (minor / serious / fatal)
- Road-user groups (e.g. motorcyclists)
- Merge the two vehicle-type columns
- Remove freeway collisions (337 rows)
- Hit-and-run yes/no flag
- Check `injured`/`killed` totals against the listed people
- Outliers in `injured` (122 and 180)
- Separate collision-level file
