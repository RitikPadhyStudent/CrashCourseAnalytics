# Tableau Public Analytics Dashboards

This document details the three Tableau Public interactive dashboards embedded into the project website, authored by Kyle VanDillen for the **Crash Course Analytics** project.

---

## 1. Fatal Collisions: Date & Time Patterns

* **Dashboard Title:** Date & Time Distribution of Fatal Accidents in SD County
* **Tableau Public URL:** [https://public.tableau.com/app/profile/kyle.vandillen/viz/SDCountyFatalAccidents/DateTimeFatal](https://public.tableau.com/app/profile/kyle.vandillen/viz/SDCountyFatalAccidents/DateTimeFatal)
* **Embed Resource:** `https://public.tableau.com/views/SDCountyFatalAccidents/DateTimeFatal`
* **Analytical Focus:**
  * Distribution of fatal collisions across hours of the day (temporal peaks, late-night / rush-hour risk).
  * Day-of-the-week collision concentration (weekday commute vs. weekend night patterns).
  * Seasonal and annual fluctuations in fatality rates across San Diego County.

---

## 2. Fatal vs. Non-Fatal Collisions

* **Dashboard Title:** Fatal vs. Non-Fatal Collisions
* **Tableau Public URL:** [https://public.tableau.com/app/profile/kyle.vandillen/viz/Fatalvs_NonFatal/Fatalvs_Non-Fatal?publish=yes](https://public.tableau.com/app/profile/kyle.vandillen/viz/Fatalvs_NonFatal/Fatalvs_Non-Fatal?publish=yes)
* **Embed Resource:** `https://public.tableau.com/views/Fatalvs_NonFatal/Fatalvs_Non-Fatal`
* **Analytical Focus:**
  * Comparative breakdown of injury severity levels across road-user roles (pedestrians, cyclists, motorcyclists, vehicle occupants).
  * Impact of environmental conditions, lighting, and hit-and-run occurrences on collision outcomes.
  * Contrast between high collision frequency locations and high fatality risk locations.

---

## 3. Primary Collision Factors & Charge Descriptions

* **Dashboard Title:** Primary Collision Factors & Charge Descriptions
* **Tableau Public URL:** [https://public.tableau.com/app/profile/kyle.vandillen/viz/ChargeDescriptions/ChargeDescription?publish=yes](https://public.tableau.com/app/profile/kyle.vandillen/viz/ChargeDescriptions/ChargeDescription?publish=yes)
* **Embed Resource:** `https://public.tableau.com/views/ChargeDescriptions/ChargeDescription`
* **Analytical Focus:**
  * Analysis of cited vehicle code violations and primary collision factors (PCFs).
  * Frequency analysis of specific charge descriptions (e.g., speeding, failure to yield, improper turning, DUI).
  * Correlation between specific charges and resulting injury severity.

---

## Integration on the Website

The dashboards are embedded on two chapter pages: the date & time dashboard on `website/map.html` (chapter 1, "Where and when"), and the fatal vs. non-fatal and charge-description dashboards on `website/tableau.html` (chapter 2, "Who and why"). They use the modern [Tableau Embedding API v3](https://public.tableau.com/javascripts/api/tableau.embedding.3.latest.min.js) web component:

```html
<tableau-viz 
  id="tableauViz"
  src="https://public.tableau.com/views/<Workbook>/<Sheet>"
  device="default"
  toolbar="bottom"
  hide-tabs>
</tableau-viz>
```

Cards are fully styled with responsive wrappers in `website/assets/css/style.css`, featuring metadata tags and direct links to open the visualizations on Tableau Public.
