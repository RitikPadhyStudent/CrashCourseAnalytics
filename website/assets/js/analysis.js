/*
 * Interactive regression and correlation charts.
 * Data: data/regression.json and data/correlation.json (built by analysis/export_website_data.py).
 * Plain SVG, no chart library. Charts redraw when their container changes width.
 * Public API: window.AnalysisCharts.initialize(options) -> Promise
 */
(function () {
  "use strict";

  const DEFAULTS = {
    regression: "#regression-chart",
    correlation: "#correlation-chart",
    dataUrl: "data/",
  };

  const SVG_NS = "http://www.w3.org/2000/svg";
  const COLORS = { up: "#B95055", down: "#294B66", ns: "#8A949C", ink: "#18242E", soft: "#4D5B66", rule: "#D8D4CA", grid: "#ECE8DF", card: "#FFFFFF" };
  // Diverging ramp for correlations: blue (negative) -> neutral gray -> red (positive)
  const RAMP = [[-1, "#1F3A52"], [-0.5, "#7D9CB6"], [0, "#F0EFEC"], [0.5, "#D7979A"], [1, "#8E3439"]];

  // ---------- small helpers ----------

  function el(tag, attrs, parent) {
    const node = tag.startsWith("svg:") ? document.createElementNS(SVG_NS, tag.slice(4)) : document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "text") node.textContent = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v);
    }
    if (parent) parent.appendChild(node);
    return node;
  }
  const svgEl = (tag, attrs, parent) => el("svg:" + tag, attrs, parent);

  function hexToRgb(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rampColor(v) {
    const x = Math.max(-1, Math.min(1, v));
    for (let i = 1; i < RAMP.length; i++) {
      const [x1, c1] = RAMP[i];
      const [x0, c0] = RAMP[i - 1];
      if (x <= x1) {
        const t = (x - x0) / (x1 - x0);
        const a = hexToRgb(c0);
        const b = hexToRgb(c1);
        return `rgb(${a.map((ai, j) => Math.round(ai + (b[j] - ai) * t)).join(",")})`;
      }
    }
    return RAMP[RAMP.length - 1][1];
  }
  const inkOn = (v) => (Math.abs(v) >= 0.55 ? "#FFFFFF" : COLORS.ink);

  const fmtOR = (x) => (x >= 10 ? x.toFixed(1) : x.toFixed(2)) + "×";
  const fmtRho = (r) => (r >= 0 ? "+" : "−") + Math.abs(r).toFixed(2);
  function fmtP(p) {
    if (p < 0.001) return "p < .001";
    return "p = " + p.toFixed(3).replace(/^0/, "");
  }
  function fmtValue(v) {
    if (v === null || v === undefined) return "no data";
    const a = Math.abs(v);
    if (a >= 1000) return Math.round(v).toLocaleString("en-US");
    if (a >= 10) return v.toFixed(1);
    return v.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  // One shared tooltip for both charts
  let tip = null;
  function showTip(html, x, y) {
    if (!tip) tip = el("div", { class: "an-tip", role: "status" }, document.body);
    tip.innerHTML = html;
    tip.hidden = false;
    const pad = 14;
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    let left = x + pad;
    let top = y + pad;
    if (left + w > window.innerWidth - 8) left = Math.max(8, x - w - pad);
    if (top + h > window.innerHeight - 8) top = Math.max(8, y - h - pad);
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }
  function hideTip() {
    if (tip) tip.hidden = true;
  }
  function tipAtElement(html, node) {
    const r = node.getBoundingClientRect();
    showTip(html, r.left + Math.min(r.width, 260) / 2, r.top + r.height / 2);
  }

  /** Segmented radio control in the same style as the map's metric chips. */
  function segmented(parent, legend, name, options, value, onChange) {
    const fs = el("fieldset", { class: "cd-seg" }, parent);
    el("legend", { text: legend }, fs);
    const row = el("div", { class: "cd-seg__row" }, fs);
    for (const opt of options) {
      const label = el("label", { class: "cd-seg__opt" }, row);
      el("input", {
        type: "radio", name, value: opt.value, checked: opt.value === value ? "checked" : null,
        onchange: () => onChange(opt.value),
      }, label);
      el("span", { text: opt.label }, label);
    }
    return fs;
  }

  /** Width inside the padding, so charts never spill past their box. */
  function innerWidth(node) {
    const cs = getComputedStyle(node);
    return node.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  }

  function onResize(node, draw) {
    let last = 0;
    new ResizeObserver(() => {
      const w = Math.round(node.clientWidth);
      if (w && w !== last) {
        last = w;
        draw();
      }
    }).observe(node);
  }

  // ---------- regression: odds-ratio chart ----------

  function regressionChart(root, data) {
    const state = { model: "serious_or_fatal", order: "group" };
    root.classList.add("an");
    root.innerHTML = "";

    const bar = el("div", { class: "an__bar" }, root);
    segmented(bar, "Outcome", "an-outcome", [
      { value: "serious_or_fatal", label: "Serious or fatal" },
      { value: "fatal", label: "Fatal only" },
    ], state.model, (v) => { state.model = v; draw(); });
    segmented(bar, "Order", "an-order", [
      { value: "group", label: "By topic" },
      { value: "size", label: "By effect size" },
    ], state.order, (v) => { state.order = v; draw(); });

    const legend = el("div", { class: "an-legend" }, root);
    legend.innerHTML =
      `<span><i class="an-dot" style="background:${COLORS.up}"></i>Raises the odds</span>` +
      `<span><i class="an-dot" style="background:${COLORS.down}"></i>Lowers the odds</span>` +
      `<span><i class="an-dot an-dot--hollow" style="border-color:${COLORS.ns}"></i>No clear effect (range crosses 1×)</span>`;

    const box = el("div", { class: "an__plot" }, root);
    const summary = el("p", { class: "an-note" }, root);
    const details = el("details", { class: "an-table" }, root);
    el("summary", { text: "Show the numbers as a table" }, details);
    const tableBox = el("div", { class: "an-table__scroll" }, details);

    // One fixed scale for both models, so switching does not move the axis
    const all = Object.values(data.models).flatMap((m) => m.rows);
    const lo = Math.min(0.05, ...all.map((r) => r.ci_low));
    const hi = Math.max(16, ...all.map((r) => r.ci_high));
    const ticks = [0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16].filter((t) => t >= lo && t <= hi);

    function rows() {
      const model = data.models[state.model];
      const list = model.rows.slice();
      if (state.order === "size") {
        list.sort((a, b) => Math.abs(Math.log(b.odds_ratio)) - Math.abs(Math.log(a.odds_ratio)));
        return list.map((r) => ({ type: "row", row: r }));
      }
      const out = [];
      for (const group of ["Who was hurt", "The crash", "The place"]) {
        out.push({ type: "head", text: group });
        list.filter((r) => r.group === group)
          .sort((a, b) => b.odds_ratio - a.odds_ratio)
          .forEach((r) => out.push({ type: "row", row: r }));
      }
      return out;
    }

    function sentence(r, outcome) {
      const range = `${fmtOR(r.ci_low)} to ${fmtOR(r.ci_high)}`;
      if (r.p_value >= 0.05) {
        return `<p>No clear difference. Compared with ${r.compared_with}, the odds of a ${outcome} could be anywhere from ${range}, and that range includes 1× (no effect).</p>`;
      }
      if (r.odds_ratio >= 1) {
        return `<p><b>${r.name}</b> have <b>${fmtOR(r.odds_ratio)}</b> the odds of a ${outcome} compared with ${r.compared_with}.</p>` +
          `<p class="an-tip__soft">Likely range: ${range} · ${fmtP(r.p_value)}</p>`;
      }
      const pct = Math.round((1 - r.odds_ratio) * 100);
      return `<p><b>${r.name}</b> have about <b>${pct}% lower</b> odds of a ${outcome} than ${r.compared_with} (${fmtOR(r.odds_ratio)}).</p>` +
        `<p class="an-tip__soft">Likely range: ${range} · ${fmtP(r.p_value)}</p>`;
    }

    function colorOf(r) {
      if (r.p_value >= 0.05) return COLORS.ns;
      return r.odds_ratio >= 1 ? COLORS.up : COLORS.down;
    }

    function draw() {
      hideTip();
      const model = data.models[state.model];
      const items = rows();
      const width = Math.max(300, innerWidth(box));
      const narrow = width < 640;
      const labelW = narrow ? Math.min(150, width * 0.42) : 260;
      const valueW = 56;
      const rowH = narrow ? 34 : 32;
      const headH = 34;
      const top = 8;
      const axisH = 40;
      const plotL = labelW + 12;
      const plotR = width - valueW;
      const height = top + items.reduce((h, it) => h + (it.type === "head" ? headH : rowH), 0) + axisH;
      const x = (v) => plotL + ((Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))) * (plotR - plotL);

      box.innerHTML = "";
      const svg = svgEl("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
        "aria-label": `Odds ratios for a ${model.outcome}. A table version follows.` }, box);

      const plotBottom = height - axisH;
      for (const t of ticks) {
        svgEl("line", { x1: x(t), x2: x(t), y1: top, y2: plotBottom, stroke: t === 1 ? COLORS.soft : COLORS.grid, "stroke-width": t === 1 ? 1.5 : 1 }, svg);
        svgEl("text", { x: x(t), y: plotBottom + 18, "text-anchor": "middle", class: "an-axis", text: `${t}×` }, svg);
      }
      svgEl("text", { x: x(1), y: plotBottom + 34, "text-anchor": "middle", class: "an-axis an-axis--note", text: "← lower odds   ·   higher odds →" }, svg);

      let y = top;
      for (const it of items) {
        if (it.type === "head") {
          svgEl("text", { x: 0, y: y + headH - 10, class: "an-group", text: it.text.toUpperCase() }, svg);
          y += headH;
          continue;
        }
        const r = it.row;
        const cy = y + rowH / 2;
        const color = colorOf(r);
        const sig = r.p_value < 0.05;
        const g = svgEl("g", { class: "an-row", tabindex: 0, role: "button", "aria-label": `${r.label}: ${fmtOR(r.odds_ratio)}` }, svg);
        svgEl("rect", { x: 0, y, width, height: rowH, class: "an-row__hit" }, g);
        const label = svgEl("text", { x: labelW, y: cy + 4, "text-anchor": "end", class: "an-label" + (sig ? "" : " an-label--ns") }, g);
        label.textContent = r.label;
        if (narrow) fitText(label, labelW);
        svgEl("line", { x1: x(r.ci_low), x2: x(r.ci_high), y1: cy, y2: cy, stroke: color, "stroke-width": 2.5, "stroke-linecap": "round" }, g);
        svgEl("circle", { cx: x(r.odds_ratio), cy, r: 6.5, fill: sig ? color : COLORS.card, stroke: sig ? COLORS.card : color, "stroke-width": sig ? 2 : 2.5 }, g);
        svgEl("text", { x: width, y: cy + 4, "text-anchor": "end", class: "an-value" + (sig ? "" : " an-label--ns"), text: fmtOR(r.odds_ratio) }, g);

        const html = `<p class="an-tip__title">${r.label}</p>` + sentence(r, model.outcome) +
          (r.note ? `<p class="an-tip__note">${r.note}</p>` : "");
        g.addEventListener("pointermove", (e) => showTip(html, e.clientX, e.clientY));
        g.addEventListener("pointerleave", hideTip);
        g.addEventListener("focus", () => tipAtElement(html, g));
        g.addEventListener("blur", hideTip);
        y += rowH;
      }

      summary.innerHTML =
        `Each row compares people in <b>otherwise similar crashes</b>, ${data.years}: ${data.people.toLocaleString("en-US")} injured people, ` +
        `${model.events.toLocaleString("en-US")} with a ${model.outcome}. Road users are compared with drivers. ` +
        `Model accuracy (AUC): ${model.auc} on a scale where 0.5 is a coin flip and 1 is perfect.`;
      drawTable(model);
    }

    function drawTable(model) {
      const rowsHtml = model.rows.slice().sort((a, b) => b.odds_ratio - a.odds_ratio).map((r) =>
        `<tr><th scope="row">${r.label}</th><td>${fmtOR(r.odds_ratio)}</td><td>${fmtOR(r.ci_low)} – ${fmtOR(r.ci_high)}</td>` +
        `<td>${fmtP(r.p_value)}</td><td>${r.p_value < 0.05 ? (r.odds_ratio >= 1 ? "Raises" : "Lowers") : "No clear effect"}</td></tr>`).join("");
      tableBox.innerHTML = `<table><thead><tr><th>Factor</th><th>Odds ratio</th><th>Likely range (95%)</th><th>p-value</th><th>Effect</th></tr></thead><tbody>${rowsHtml}</tbody></table>`;
    }

    onResize(box, draw);
  }

  /** Shorten an SVG label with an ellipsis until it fits. */
  function fitText(node, maxW) {
    const full = node.textContent;
    let text = full;
    while (text.length > 4 && node.getComputedTextLength() > maxW) {
      text = text.slice(0, -2);
      node.textContent = text + "…";
    }
    if (text !== full) svgEl("title", { text: full }, node);
  }

  // ---------- correlation: Y list, full matrix and beat scatter ----------

  function correlationChart(root, data) {
    const vars = data.variables;
    const yIndex = vars.findIndex((v) => v.key === data.y);
    const groups = [...new Set(vars.map((v) => v.group))].filter((g) => g !== "Outcome");
    const state = {
      view: "y",
      groups: new Set(groups),
      onlyClear: false,
      pair: [vars.findIndex((v) => v.key === "pop_per_sq_mi"), yIndex],
      ranks: false,
    };
    root.classList.add("an");
    root.innerHTML = "";

    const bar = el("div", { class: "an__bar" }, root);
    segmented(bar, "View", "an-view", [
      { value: "y", label: "Link with the injury rate" },
      { value: "matrix", label: "Every pair (heatmap)" },
    ], state.view, (v) => { state.view = v; draw(); });

    const filters = el("fieldset", { class: "cd-seg" }, bar);
    el("legend", { text: "Show variables about" }, filters);
    const chipRow = el("div", { class: "cd-seg__row" }, filters);
    for (const g of groups) {
      const label = el("label", { class: "cd-seg__opt" }, chipRow);
      el("input", {
        type: "checkbox", checked: "checked",
        onchange: (e) => {
          if (e.target.checked) state.groups.add(g);
          else state.groups.delete(g);
          draw();
        },
      }, label);
      el("span", { text: g }, label);
    }
    const clearLabel = el("label", { class: "an-check" }, filters);
    el("input", { type: "checkbox", onchange: (e) => { state.onlyClear = e.target.checked; draw(); } }, clearLabel);
    el("span", { text: "Only clear links (p < .05)" }, clearLabel);

    const scale = el("div", { class: "an-scale" }, root);
    scale.innerHTML =
      `<span>−1 (opposite)</span><i style="background:linear-gradient(90deg,${RAMP.map(([v, c]) => `${c} ${(v + 1) * 50}%`).join(",")})"></i><span>+1 (together)</span>`;

    const main = el("div", { class: "an__split" }, root);
    const box = el("div", { class: "an__plot an__plot--scroll" }, main);
    const side = el("div", { class: "an__side" }, main);
    const note = el("p", { class: "an-note" }, root);

    const visible = () => vars.map((v, i) => i).filter((i) => i === yIndex || state.groups.has(vars[i].group));
    const strength = (r) => {
      const a = Math.abs(r);
      if (a < 0.1) return "no real link";
      return (a < 0.3 ? "a weak" : a < 0.5 ? "a moderate" : "a strong") + (r > 0 ? " positive link" : " negative link");
    };

    function pairHtml(i, j) {
      const r = data.rho[i][j];
      const p = data.p[i][j];
      const a = vars[i];
      const b = vars[j];
      const clear = p < 0.05;
      const direction = r > 0 ? "higher" : "lower";
      let meaning;
      if (Math.abs(r) < 0.1) meaning = `Beats with more of one show no real pattern in the other.`;
      else meaning = `Beats with a higher <b>${a.label.toLowerCase()}</b> tend to have a ${direction} <b>${b.label.replace(/^Y: /, "").toLowerCase()}</b>.`;
      return `<p class="an-tip__title">${a.label} × ${b.label}</p>` +
        `<p><b>${fmtRho(r)}</b> · ${strength(r)}</p><p>${meaning}</p>` +
        `<p class="an-tip__soft">${clear ? "Clear link" : "Could be chance"} (${fmtP(p)}, ${data.n[i][j]} beats)</p>` +
        `<p class="an-tip__soft">Click to see the beats behind it.</p>`;
    }

    function select(i, j) {
      state.pair = [i, j];
      drawScatter();
      draw();
    }

    // ----- view 1: every variable's link with Y, sorted -----
    function drawYList(width) {
      let idx = visible().filter((i) => i !== yIndex);
      if (state.onlyClear) idx = idx.filter((i) => data.p[i][yIndex] < 0.05);
      idx.sort((a, b) => data.rho[b][yIndex] - data.rho[a][yIndex]);
      const narrow = width < 560;
      const labelW = narrow ? Math.min(150, width * 0.45) : 240;
      const valueW = 58;
      const rowH = 26;
      const top = 22;
      const height = top + idx.length * rowH + 8;
      const mid = labelW + 12 + (width - labelW - 12 - valueW) / 2;
      const half = (width - labelW - 12 - valueW) / 2;

      const svg = svgEl("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
        "aria-label": "Correlation of each variable with the serious/fatal injury rate, sorted." }, box);
      svgEl("text", { x: mid - half, y: 12, class: "an-axis", text: "−1" }, svg);
      svgEl("text", { x: mid, y: 12, class: "an-axis", "text-anchor": "middle", text: "0" }, svg);
      svgEl("text", { x: mid + half, y: 12, class: "an-axis", "text-anchor": "end", text: "+1" }, svg);
      svgEl("line", { x1: mid, x2: mid, y1: top - 4, y2: height - 4, stroke: COLORS.soft }, svg);

      idx.forEach((i, k) => {
        const r = data.rho[i][yIndex];
        const p = data.p[i][yIndex];
        const y = top + k * rowH;
        const selected = state.pair[0] === i && state.pair[1] === yIndex;
        const g = svgEl("g", { class: "an-row" + (selected ? " is-selected" : ""), tabindex: 0, role: "button",
          "aria-label": `${vars[i].label}: ${fmtRho(r)}` }, svg);
        svgEl("rect", { x: 0, y, width, height: rowH, class: "an-row__hit" }, g);
        const label = svgEl("text", { x: labelW, y: y + rowH / 2 + 4, "text-anchor": "end", class: "an-label" + (p < 0.05 ? "" : " an-label--ns") }, g);
        label.textContent = vars[i].label;
        if (narrow) fitText(label, labelW);
        const w = Math.abs(r) * half;
        svgEl("rect", { x: r >= 0 ? mid : mid - w, y: y + 5, width: Math.max(w, 1), height: rowH - 10, rx: 3, fill: rampColor(r >= 0 ? Math.max(r, 0.35) : Math.min(r, -0.35)), opacity: p < 0.05 ? 1 : 0.45 }, g);
        svgEl("text", { x: width, y: y + rowH / 2 + 4, "text-anchor": "end", class: "an-value" + (p < 0.05 ? "" : " an-label--ns"),
          text: fmtRho(r) + (p < 0.01 ? "**" : p < 0.05 ? "*" : "") }, g);
        const html = pairHtml(i, yIndex);
        g.addEventListener("pointermove", (e) => showTip(html, e.clientX, e.clientY));
        g.addEventListener("pointerleave", hideTip);
        g.addEventListener("focus", () => tipAtElement(html, g));
        g.addEventListener("blur", hideTip);
        g.addEventListener("click", () => select(i, yIndex));
        g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(i, yIndex); } });
      });
      if (!idx.length) svgEl("text", { x: 0, y: top + 16, class: "an-label", text: "No variables match these filters." }, svg);
      note.innerHTML = `Bars show how strongly each beat characteristic moves with the <b>serious/fatal injury rate</b> across ${data.n_beats} police beats (Spearman). ` +
        `* p < .05, ** p < .01. Faded bars could be chance. Click a row to see the beats behind it.`;
    }

    // ----- view 2: full lower-triangle heatmap -----
    function drawMatrix(width) {
      const idx = visible();
      const k = idx.length;
      const labelW = width < 560 ? 130 : 210;
      const cell = Math.max(14, Math.min(30, Math.floor((width - labelW - 8) / k)));
      const colLabelH = labelW * 0.8;
      const w = labelW + cell * k + 8;
      const h = cell * k + colLabelH;
      const svg = svgEl("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: "img",
        "aria-label": "Correlation heatmap of every pair of variables." }, box);

      const rowLabels = [];
      const colLabels = [];
      idx.forEach((vi, a) => {
        const t = svgEl("text", { x: labelW - 6, y: a * cell + cell / 2 + 4, "text-anchor": "end", class: "an-label an-label--sm" + (vi === yIndex ? " an-label--y" : "") }, svg);
        t.textContent = vars[vi].label;
        fitText(t, labelW - 8);
        rowLabels.push(t);
        const cx = labelW + a * cell + cell / 2;
        const c = svgEl("text", { x: cx, y: k * cell + 8, transform: `rotate(-55 ${cx} ${k * cell + 8})`, "text-anchor": "end",
          class: "an-label an-label--sm" + (vi === yIndex ? " an-label--y" : "") }, svg);
        c.textContent = vars[vi].label;
        fitText(c, colLabelH - 8);
        colLabels.push(c);
      });

      const showNumbers = cell >= 26;
      idx.forEach((vi, a) => {
        for (let b = 0; b <= a; b++) {
          const vj = idx[b];
          const r = data.rho[vi][vj];
          const p = data.p[vi][vj];
          const faded = state.onlyClear && p >= 0.05 && a !== b;
          const selected = (state.pair[0] === vi && state.pair[1] === vj) || (state.pair[0] === vj && state.pair[1] === vi);
          const g = svgEl("g", { class: "an-cell" + (selected ? " is-selected" : "") }, svg);
          svgEl("rect", { x: labelW + b * cell + 1, y: a * cell + 1, width: cell - 2, height: cell - 2, rx: 2,
            fill: faded ? "#F4F2EC" : rampColor(r) }, g);
          if (showNumbers && !faded) {
            svgEl("text", { x: labelW + b * cell + cell / 2, y: a * cell + cell / 2 + 3.5, "text-anchor": "middle", class: "an-cell__num",
              fill: inkOn(r), text: a === b ? "1" : fmtRho(r).replace("0.", ".") }, g);
          }
          if (a === b) continue;
          const html = pairHtml(vi, vj);
          g.addEventListener("pointermove", (e) => {
            rowLabels[a].classList.add("is-hot");
            colLabels[b].classList.add("is-hot");
            showTip(html, e.clientX, e.clientY);
          });
          g.addEventListener("pointerleave", () => {
            rowLabels[a].classList.remove("is-hot");
            colLabels[b].classList.remove("is-hot");
            hideTip();
          });
          g.addEventListener("click", () => select(vi, vj));
        }
      });
      // Outline the Y row and column so the outcome stands out
      const ya = idx.indexOf(yIndex);
      if (ya >= 0) {
        svgEl("rect", { x: labelW + ya * cell, y: ya * cell, width: cell, height: (k - ya) * cell, fill: "none", stroke: COLORS.ink, "stroke-width": 1.5, rx: 2 }, svg);
      }
      note.innerHTML = `Every square is one pair of variables across ${data.n_beats} police beats. Red: they rise together. Blue: one rises as the other falls. ` +
        `The outlined column is the serious/fatal injury rate. Hover a square for its meaning; click it to see the beats. ` +
        `Dark squares between two inputs mean they measure almost the same thing.`;
    }

    function draw() {
      hideTip();
      box.innerHTML = "";
      const width = Math.max(280, innerWidth(box));
      if (state.view === "y") drawYList(width);
      else drawMatrix(width);
    }

    // ----- side panel: scatter of the selected pair, one dot per beat -----
    function drawScatter() {
      const [i, j] = state.pair;
      side.innerHTML = "";
      const head = el("div", { class: "an-side__head" }, side);
      el("p", { class: "an-side__title", text: `${vars[i].label} vs ${vars[j].label.replace(/^Y: /, "")}` }, head);
      el("p", { class: "an-side__meta", html: `<b>${fmtRho(data.rho[i][j])}</b> · ${strength(data.rho[i][j])} · ${fmtP(data.p[i][j])}` }, head);
      const toggle = el("label", { class: "an-check" }, head);
      el("input", { type: "checkbox", checked: state.ranks ? "checked" : null, onchange: (e) => { state.ranks = e.target.checked; drawScatter(); } }, toggle);
      el("span", { text: "Show ranks (what Spearman compares)" }, toggle);

      const pts = data.beats
        .map((b) => ({ name: b.name, beat: b.beat, x: b.values[i], y: b.values[j] }))
        .filter((p) => p.x !== null && p.y !== null);
      if (state.ranks) {
        const rank = (key) => {
          const sorted = pts.map((p, k) => [p[key], k]).sort((a, b) => a[0] - b[0]);
          const out = new Array(pts.length);
          let s = 0;
          while (s < sorted.length) {
            let e = s;
            while (e + 1 < sorted.length && sorted[e + 1][0] === sorted[s][0]) e++;
            for (let q = s; q <= e; q++) out[sorted[q][1]] = (s + e) / 2 + 1;
            s = e + 1;
          }
          return out;
        };
        const rx = rank("x");
        const ry = rank("y");
        pts.forEach((p, k) => { p.rx = rx[k]; p.ry = ry[k]; });
      }

      const width = Math.max(240, innerWidth(side));
      const height = Math.min(360, Math.max(240, width * 0.85));
      const m = { l: 46, r: 12, t: 12, b: 40 };
      const xs = pts.map((p) => (state.ranks ? p.rx : p.x));
      const ys = pts.map((p) => (state.ranks ? p.ry : p.y));
      const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
      const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
      const sx = (v) => m.l + ((v - x0) / (x1 - x0 || 1)) * (width - m.l - m.r);
      const sy = (v) => height - m.b - ((v - y0) / (y1 - y0 || 1)) * (height - m.t - m.b);

      const svg = svgEl("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
        "aria-label": `Scatter plot of ${vars[i].label} against ${vars[j].label}, one dot per police beat.` }, side);
      svgEl("rect", { x: m.l, y: m.t, width: width - m.l - m.r, height: height - m.t - m.b, fill: "#FAF9F6", stroke: COLORS.grid }, svg);
      const axisVal = (v) => (state.ranks ? Math.round(v) : fmtValue(v));
      svgEl("text", { x: m.l, y: height - m.b + 16, class: "an-axis", text: axisVal(x0) }, svg);
      svgEl("text", { x: width - m.r, y: height - m.b + 16, class: "an-axis", "text-anchor": "end", text: axisVal(x1) }, svg);
      svgEl("text", { x: m.l - 6, y: height - m.b, class: "an-axis", "text-anchor": "end", text: axisVal(y0) }, svg);
      svgEl("text", { x: m.l - 6, y: m.t + 10, class: "an-axis", "text-anchor": "end", text: axisVal(y1) }, svg);
      const xl = svgEl("text", { x: (m.l + width - m.r) / 2, y: height - 8, class: "an-axis", "text-anchor": "middle" }, svg);
      xl.textContent = (state.ranks ? "Rank: " : "") + vars[i].label + " →";
      fitText(xl, width - m.l - m.r);
      const ylab = svgEl("text", { x: 12, y: (m.t + height - m.b) / 2, class: "an-axis", "text-anchor": "middle", transform: `rotate(-90 12 ${(m.t + height - m.b) / 2})` }, svg);
      ylab.textContent = (state.ranks ? "Rank: " : "") + vars[j].label.replace(/^Y: /, "") + " →";
      fitText(ylab, height - m.t - m.b);

      // Least-squares trend line on whatever is plotted, as a visual guide only
      const n = xs.length;
      const mx = xs.reduce((a, b) => a + b, 0) / n;
      const my = ys.reduce((a, b) => a + b, 0) / n;
      let num = 0;
      let den = 0;
      xs.forEach((xv, k) => { num += (xv - mx) * (ys[k] - my); den += (xv - mx) ** 2; });
      if (den > 0) {
        const slope = num / den;
        const clampY = (v) => Math.max(y0, Math.min(y1, v));
        svgEl("line", { x1: sx(x0), y1: sy(clampY(my + slope * (x0 - mx))), x2: sx(x1), y2: sy(clampY(my + slope * (x1 - mx))),
          stroke: data.rho[i][j] >= 0 ? COLORS.up : COLORS.down, "stroke-width": 2, "stroke-dasharray": "5 4", opacity: 0.8 }, svg);
      }

      pts.forEach((p, k) => {
        const c = svgEl("circle", { cx: sx(xs[k]), cy: sy(ys[k]), r: 5, class: "an-pt" }, svg);
        const html = `<p class="an-tip__title">${p.name} <span class="an-tip__soft">beat ${p.beat}</span></p>` +
          `<p>${vars[i].label}: <b>${fmtValue(p.x)}</b></p><p>${vars[j].label.replace(/^Y: /, "")}: <b>${fmtValue(p.y)}</b></p>`;
        c.addEventListener("pointermove", (e) => showTip(html, e.clientX, e.clientY));
        c.addEventListener("pointerleave", hideTip);
      });
      el("p", { class: "an-note", text: `Each dot is one police beat (${pts.length}). The dashed line shows the overall direction. Hover a dot to see which beat it is.` }, side);
    }

    onResize(box, draw);
    onResize(side, drawScatter);
  }

  // ---------- entry point ----------

  async function initialize(options) {
    const opts = Object.assign({}, DEFAULTS, options);
    const base = opts.dataUrl.endsWith("/") ? opts.dataUrl : opts.dataUrl + "/";
    const load = async (name) => {
      const res = await fetch(base + name);
      if (!res.ok) throw new Error(`Could not load ${name} (HTTP ${res.status})`);
      return res.json();
    };
    const jobs = [];
    const reg = document.querySelector(opts.regression);
    const cor = document.querySelector(opts.correlation);
    const fail = (node) => (err) => {
      node.innerHTML = `<p class="cd-error">Could not load this chart: ${err.message}</p>`;
      throw err;
    };
    if (reg) jobs.push(load("regression.json").then((d) => regressionChart(reg, d)).catch(fail(reg)));
    if (cor) jobs.push(load("correlation.json").then((d) => correlationChart(cor, d)).catch(fail(cor)));
    document.addEventListener("scroll", hideTip, { passive: true });
    return Promise.all(jobs);
  }

  window.AnalysisCharts = { initialize };
})();
