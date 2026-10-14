# Crash Course Analytics website

A static website (plain HTML, CSS and JavaScript) that tells the project's story in five chapters, one page each. It is deployed on Vercel from the `website/` folder on `main`.

| Page | Chapter | What it shows |
|---|---|---|
| `index.html` | Home | The project question, key numbers, the five chapters, the short version of the findings, the team |
| `map.html` | 1 · Where & when | The police-beat map (below), its findings, and Kyle's date & time Tableau dashboard |
| `tableau.html` | 2 · Who & why | Kyle's fatal vs. non-fatal and charge-description Tableau dashboards |
| `correlation.html` | 3 · Correlation | Interactive correlations between each beat's serious/fatal injury rate and 44 beat characteristics |
| `regression.html` | 4 · Regression | Interactive odds-ratio chart from the logistic regression |
| `methods.html` | 5 · Methods | How every chapter's numbers were built, and their limits |

Every page shares the sticky top bar (`assets/css/nav.css`). Chapter pages also show a progress bar, a "What this chapter tells us" box and previous/next links (`assets/css/story.css`). The chapter text lives in each page's HTML.

## The beat map (chapter 1)

An interactive dashboard (Leaflet and Chart.js) for exploring **collision frequency and injury severity by San Diego police beat, 2018–2025**.

What a visitor can do:

- **Switch metric:** collision frequency, serious/fatal injury rate, fatal injury rate, serious/fatal records, fatal records.
- **Move through time:** drag the year slider, or press ▶ to animate 2018 → 2025.
- **Explore beats:** hover to highlight a beat; click it for a popup with all its values. Clicking a beat also draws its 2018–2025 trend chart.
- **Rank beats:** the panel lists the top 10 beats for the current metric and year. Click one to zoom to it.
- **Jump to a year from the chart:** click a year in the city-wide trend chart to show that year on the map.

The site publishes **aggregated summaries only** (beat-years, beats and model results). It contains no collision-level or participant-level records.

## How to run in on your computer for Ritik and Kyle

You need Python (any 3.x) and an internet connection, because the basemap, Leaflet, Chart.js and fonts load from CDNs.

1. Open a terminal (PowerShell, Command Prompt or Git Bash) in the project folder `D:\desktop\BDA\Groupproject`. Change it to your own path.
2. Start a local web server:

   ```bash
   python -m http.server 8000 --directory website
   ```

   If `python` is not found, use the project environment instead: `.venv\Scripts\python.exe -m http.server 8000 --directory website`.
3. Open <http://localhost:8000> in a browser.
4. Press `Ctrl+C` in the terminal to stop the server.

Opening `index.html` by double-clicking does **not** work: browsers block loading the data files from `file://` pages.

## Folder structure

```
website/
├── index.html                      Home page
├── map.html                        Chapter 1: beat map, its findings, date & time dashboard
├── tableau.html                    Chapter 2: Tableau dashboards
├── correlation.html                Chapter 3: correlation charts
├── regression.html                 Chapter 4: regression chart
├── methods.html                    Chapter 5: methods and limitations
├── assets/
│   ├── css/style.css               Base styles, map dashboard ("cd-" prefix) and Tableau cards
│   ├── css/nav.css                 Top bar and previous/next links
│   ├── css/story.css               Chapter progress bar and takeaway box
│   ├── css/home.css                Home page
│   ├── css/analysis.css            Correlation and regression charts ("an-" prefix)
│   ├── js/app.js                   Map dashboard logic; exposes window.CollisionDashboard
│   └── js/analysis.js              Correlation and regression charts; exposes window.AnalysisCharts
├── data/
│   ├── police_beats_web.geojson    One simplified polygon per SDPD police beat (125 beats)
│   ├── map_properties.json         Beat-year summaries 2018-2025, metric definitions, class breaks
│   ├── annual_trends.json          City-wide annual totals 2018-2025
│   ├── insights.json               Findings shown below the map (generated)
│   ├── correlation.json            Correlation matrix and beat values (analysis/export_website_data.py)
│   └── regression.json             Odds ratios for both models (analysis/export_website_data.py)
└── README.md
```

The ArcGIS Pro project (`Spatial_Rong/`) is separate and is not used or modified by the website.

## Data fields

### `police_beats_web.geojson`

| Field | Meaning |
|---|---|
| `police_beat` | Integer police-beat code; the join key. One feature per SDPD beat (125). |

The geometry is built by `scripts/build_police_beats_web.py` from the City of San Diego police-beat file, keeping **SDPD beats only** (`div` > 0). It is dissolved by beat, simplified (about 12 m), rounded to 1e-5° and stored in WGS84.

**Why SDPD only:** the city file also contains county sheriff beats that reuse SDPD beat numbers (821 is both Rolando and Santa Ysabel). The earlier geometry, from `police_beats_2016_analysis.geojson`, used the county polygon for 83 of the 125 SDPD beats, so their collisions were drawn up to 57 miles away. Do not rebuild the geometry from that file.

### `map_properties.json`

| Key | Meaning |
|---|---|
| `years` | Years available on the slider (2018-2025) |
| `min_known_injury_records` | Rate eligibility threshold (30) |
| `beats_without_polygon` | Beat codes that have records but no boundary (not drawn) |
| `metrics` | One entry per map metric: `key`, `label`, `field`, `rate`, `note`, and `classes` (`name`, `range`, `max` upper bound, `color`, `count`) |
| `records` | One row per beat-year (fields below) |

| Record field | Meaning |
|---|---|
| `year`, `police_beat` | Join key with the GeoJSON |
| `unique_collisions` | Distinct `report_id` values |
| `participant_records` | Participant rows |
| `known_injury_records` | Participants with known injury status (rate denominator) |
| `serious_fatal_records` | Participants with serious/severe or fatal injury |
| `fatal_records` | Participants with fatal injury |
| `serious_fatal_rate` | `serious_fatal_records / known_injury_records` (`null` if the denominator is 0) |
| `fatal_rate` | `fatal_records / known_injury_records` (`null` if the denominator is 0) |

**Classes** are relative and pooled over all 2018–2025 beat-years, so a colour means the same value range in every year:

- *Collision frequency* and *serious/fatal rate*: quintiles (Very low … Very high), using the colours from the project brief.
- *Fatal rate*, *serious/fatal records* and *fatal records*: most beat-years are zero, so zero is its own class and the non-zero values are split into quartiles.
- Rates are classified only for beat-years with at least 30 known injury records. All others are shown as *Not eligible*.
- A beat with no record in the selected year is shown as *No collision summary*.

### `annual_trends.json`

One object per year with `unique_collisions`, `participant_records`, `known_injury_records`, `serious_fatal_records`, `fatal_records`, `serious_fatal_rate` and `fatal_rate`.

### `insights.json`

`{ "sections": [ { "title": "...", "bullets": ["..."] } ] }`

## Update the data

Everything in `website/data/` is generated by one script that reads only the aggregated tables:

```bash
# from the project root
.venv\Scripts\python.exe code\build_website_data.py      # Windows
.venv/bin/python code/build_website_data.py              # macOS/Linux
```

Inputs (the 2016-2025 tables are filtered to `FIRST_YEAR = 2018` and later):

- `code/outputs/tables/police_beat_year_summary_2016_2025.csv`
- `code/outputs/tables/annual_trends_2016_2025.csv`
- `code/data/processed/spatial/police_beats_2016_analysis.geojson` (geometry only)

The script checks that beats are unique and geometries valid, that eligibility matches the threshold, that no class is empty, and that no `NaN` reaches the JSON. **The findings are computed from the tables**, so they stay consistent after a data refresh. Change their wording in `annual_insights()` / `beat_insights()` in the script. Hand edits to `insights.json` are overwritten on the next build.

To add or change a map metric, edit the `METRICS` list in the script (field, colours, class scheme) and rebuild. The dashboard reads metrics, classes and colours from the JSON, so no JavaScript change is needed.

## How to Embed or call the dashboard for Ritik and Kyle

`app.js` exposes one function:

```js
window.CollisionDashboard.initialize(options) // -> Promise<{ map, setYear(year), selectBeat(beat) }>
```

| Option | Default | Meaning |
|---|---|---|
| `root` | `"#collision-dashboard"` | Selector or element that receives the controls, map, legend, ranking and charts |
| `insights` | `"#findings"` | Optional selector for the findings list (skipped if missing) |
| `dataUrl` | `"data/"` | Folder (relative or absolute URL) with the four data files |
| `metric` | `"frequency"` | Initial metric key: `frequency`, `severity`, `fatal_rate`, `serious_fatal`, `fatal` |
| `year` | latest year | Initial year |

Minimal host page:

```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://<your-site>/assets/css/style.css">
<div id="collision-dashboard"></div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://<your-site>/assets/js/app.js"></script>
<script>
  CollisionDashboard.initialize({ dataUrl: "https://<your-site>/data/", metric: "severity", year: 2020 })
    .then((dash) => dash.selectBeat(122));
</script>
```

The host must be able to `fetch` from `dataUrl`; GitHub Pages allows cross-origin requests. The simplest alternative is `<iframe src="https://<your-site>/">`. Only one dashboard instance per page is supported.

## Data limitations

- Frequency counts unique `report_id` values. It is not exposure-adjusted (no traffic volume, road length or population).
- Rates use only participants with **known** injury status, which is about 24–29% of participant records.
- Rates are shown only for beat-years with at least 30 known injury records.
- Classes are **relative** to the 2018–2025 beat-year set, not absolute risk thresholds.
- Police-beat representative coordinates are not exact collision locations.
- The maps show observed patterns. They do not estimate causal danger or individual crash risk.
- 2016 and 2017 are excluded. 2017 has an unusually low number of records (240 reports, no rate-eligible beat), and 2016 is also well below later years. The cut-off is `FIRST_YEAR = 2018` in `code/build_website_data.py`.
- Beat codes that are not SDPD beats (for example 71, 200, 600, 760, 904, 999, and a few county beat numbers with one to four records each) have no polygon, so they are not drawn.

## Basemap attribution

The basemap is © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors and is loaded from the standard OSM tile server. The attribution stays visible in the map corner and must not be removed. Heavy-traffic deployments should follow the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/) or switch the tile URL in `renderMap()` in `app.js`. Map rendering uses [Leaflet](https://leafletjs.com) (BSD-2-Clause). Charts use [Chart.js](https://www.chartjs.org) (MIT).

## Rule: raw data must not be published

**Never copy collision-level or participant-level files into `website/`.** That includes anything under `code/data/raw/`, `code/data/processed/*.csv`, `code/data/processed/yearly/` and `Datasets/`. Only the aggregated outputs of `code/build_website_data.py` belong here. Before publishing, check:

```bash
ls website/data   # expect exactly the six files listed above
```
