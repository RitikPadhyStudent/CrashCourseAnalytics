"""Clean the San Diego traffic collision dataset.

Steps:
  1. Strip extra spaces from every value (space-only values become blank)
  2. Remove rows that are completely blank
  3. Remove exact duplicate rows
  4. Keep only collisions from 2015 to 2025
  5. Fix the injury label typo: VISABLE -> VISIBLE

Usage (from the repo root):
  python3 scripts/clean_data.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "dataset" / "sd_county_collision_data.csv"
CLEAN_FILE = ROOT / "dataset" / "sd_county_collision_data_clean.csv"

START_YEAR = 2015
END_YEAR = 2025


def summarize(rows, label):
    years = [row["date_time"][:4] for row in rows if row["date_time"]]
    print(f"{label}:")
    print(f"  Rows (people):        {len(rows):,}")
    print(f"  Collisions (reports): {len({row['report_id'] for row in rows}):,}")
    print(f"  Years:                {min(years)} to {max(years)}")
    print()


def main():
    with open(RAW_FILE, newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)

    summarize(rows, "Before cleaning")
    log = []

    # 1. Strip extra spaces
    changed = 0
    for row in rows:
        for col in columns:
            stripped = row[col].strip()
            if stripped != row[col]:
                row[col] = stripped
                changed += 1
    log.append(f"Stripped extra spaces:        {changed:,} values")

    # 2. Remove completely blank rows
    before = len(rows)
    rows = [row for row in rows if any(row[col] for col in columns)]
    log.append(f"Removed completely blank rows: {before - len(rows):,} rows")

    # 3. Remove exact duplicate rows
    before = len(rows)
    seen = set()
    unique_rows = []
    for row in rows:
        key = tuple(row[col] for col in columns)
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    rows = unique_rows
    log.append(f"Removed duplicate rows:        {before - len(rows):,} rows")

    # 4. Keep 2015-2025 only
    before = len(rows)
    rows = [row for row in rows if START_YEAR <= int(row["date_time"][:4]) <= END_YEAR]
    log.append(f"Removed rows outside {START_YEAR}-{END_YEAR}:  {before - len(rows):,} rows")

    # 5. Fix injury label typo
    fixed = 0
    for row in rows:
        if row["person_injury_lvl"] == "VISABLE":
            row["person_injury_lvl"] = "VISIBLE"
            fixed += 1
    log.append(f"Fixed VISABLE -> VISIBLE:      {fixed:,} values")

    with open(CLEAN_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print("Cleaning steps:")
    for line in log:
        print(f"  {line}")
    print()
    summarize(rows, "After cleaning")
    print(f"Saved: {CLEAN_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
