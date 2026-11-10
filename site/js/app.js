import * as duckdb from "@duckdb/duckdb-wasm";

import { DAY_TABLE, evaluateResults, parseGolden, runSuite } from "./engine.js";
import {
  SQL_PRESETS,
  checkDescription,
  defectDescription,
  describe,
  formatCount,
  formatDay,
  formatScore,
  metricCell,
  nodeLabel,
  severityLabel,
  statusLabel,
  t,
} from "./i18n.js";
import { rowsFrom } from "./rows.js";
import { guardSelect } from "./sql_guard.js";

const TABLES = ["hubs", "customers", "tracking_scans", "shipments", "daily_route_kpis"];
const SQL_CAP = 200;

const state = {
  lang: localStorage.getItem("rutanorte-lang") === "en" ? "en" : "es",
  ready: false,
  error: null,
  progress: { value: 0, max: 100, label: "" },
  manifest: null,
  suite: null,
  defects: [],
  counts: {},
  results: [],
  scores: [],
  evaluation: null,
  elapsedMs: 0,
  filters: { date: "all", table: "all", severity: "all", status: "fail" },
  tab: "checks",
  selectedKey: null,
  sql: SQL_PRESETS.channel,
  sqlRows: null,
  sqlColumns: [],
  sqlError: null,
  sqlTruncated: false,
  connection: null,
};

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let motionToken = 0;

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of [].concat(children)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function clear(node) {
  node.replaceChildren();
}

function dayScores() {
  return state.scores.filter((row) => row.table_name === DAY_TABLE).sort((a, b) => a.business_date.localeCompare(b.business_date));
}

function resultKey(row) {
  return `${row.business_date}|${row.check_id}`;
}

function visibleChecks() {
  return state.results.filter((row) => {
    if (state.filters.date !== "all" && row.business_date !== state.filters.date) return false;
    if (state.filters.table !== "all" && row.table_name !== state.filters.table) return false;
    if (state.filters.severity !== "all" && row.severity !== state.filters.severity) return false;
    if (state.filters.status !== "all" && row.status !== state.filters.status) return false;
    return true;
  });
}

function defectCaught(defect) {
  const row = state.results.find(
    (item) => item.check_id === defect.check_id && item.business_date === defect.business_date,
  );
  if (!row || row.status !== "fail") return { caught: false, observed: row ? row.failed_row_count : null };
  if (defect.min_failed_rows == null) return { caught: true, observed: row.failed_row_count };
  return {
    caught: Number(row.failed_row_count) >= Number(defect.min_failed_rows),
    observed: row.failed_row_count,
  };
}

function visibleDefects() {
  return state.defects.filter((defect) => {
    if (state.filters.date !== "all" && defect.business_date !== state.filters.date) return false;
    if (state.filters.table !== "all" && defect.table !== state.filters.table) return false;
    return true;
  });
}

function assetUrl(relativePath) {
  return new URL(relativePath, import.meta.url);
}

async function loadJson(relativePath) {
  const response = await fetch(assetUrl(relativePath));
  if (!response.ok) throw new Error(`${relativePath} ${response.status}`);
  return response.json();
}

async function openWarehouse() {
  const workerUrl = assetUrl("../vendor/duckdb-browser-eh.worker.js");
  const wasmUrl = assetUrl("../vendor/duckdb-eh.wasm");
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB({ log() {} }, worker);
  await db.instantiate(wasmUrl.href);
  const conn = await db.connect();
  for (const table of TABLES) {
    const response = await fetch(assetUrl(`../data/${table}.parquet`));
    if (!response.ok) throw new Error(`${table}.parquet ${response.status}`);
    const buffer = new Uint8Array(await response.arrayBuffer());
    await db.registerFileBuffer(`${table}.parquet`, buffer);
    await conn.query(`CREATE TABLE ${table} AS SELECT * FROM read_parquet('${table}.parquet')`);
  }
  state.connection = conn;
  async function query(sql) {
    return rowsFrom(await conn.query(sql));
  }
  return query;
}

function setProgress(value, max, label) {
  state.progress = { value, max, label };
  const bar = document.querySelector("#progress");
  const text = document.querySelector("#progress-label");
  if (bar) {
    bar.max = max;
    bar.value = value;
  }
  if (text) text.textContent = label;
}

async function boot() {
  document.querySelector("#title").textContent = t(state.lang, "title");
  setProgress(2, 100, t(state.lang, "progressWasm"));
  try {
    const [manifest, suite, defectFile, goldenText] = await Promise.all([
      loadJson("../data/manifest.json"),
      loadJson("../data/suite.json"),
      loadJson("../data/defects.json"),
      fetch(assetUrl("../data/golden.csv")).then((response) => {
        if (!response.ok) throw new Error(`golden.csv ${response.status}`);
        return response.text();
      }),
    ]);
    state.manifest = manifest;
    state.suite = suite;
    state.defects = defectFile.defects;
    setProgress(8, 100, t(state.lang, "progressData"));
    const query = await openWarehouse();
    for (const table of TABLES) {
      const rows = await query(`SELECT count(*)::DOUBLE AS n FROM ${table}`);
      state.counts[table] = Math.round(Number(rows[0].n));
    }
    const started = performance.now();
    const golden = parseGolden(goldenText);
    const output = await runSuite(query, suite, golden, {
      onProgress({ index, total, checkId }) {
        const span = 88;
        const value = 10 + Math.round((index / total) * span);
        setProgress(
          value,
          100,
          t(state.lang, "progressCheck", {
            check: checkId || "hubs_city_completeness",
            done: checkId ? index + 1 : total,
            total,
          }),
        );
      },
    });
    state.elapsedMs = performance.now() - started;
    state.results = output.results;
    state.scores = output.scores;
    state.evaluation = evaluateResults(output.results, state.defects);
    state.ready = true;
    paint();
    const score = document.querySelector("#lede [data-count]");
    if (score) countUp(score);
  } catch (error) {
    state.error = error;
    paint();
  }
}

function countUp(node) {
  const token = motionToken;
  const target = Number(node.dataset.count);
  const full = node.textContent;
  const formatted = formatCount(target, state.lang);
  if (!full.includes(formatted) || reduceMotion) return;
  const started = performance.now();
  function frame(now) {
    if (token !== motionToken || !node.isConnected) return;
    const progress = Math.min(1, (now - started) / 700);
    const value = Math.round(target * (1 - (1 - progress) ** 3));
    node.textContent = full.replace(formatted, formatCount(value, state.lang));
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function ledeSentences() {
  const lang = state.lang;
  const days = dayScores();
  const failingDays = days.filter((day) => day.status === "fail");
  const failingChecks = state.results.filter((row) => row.status === "fail");
  const evaluation = state.evaluation;
  const sentences = [
    t(lang, "counts", {
      shipments: formatCount(state.counts.shipments, lang),
      customers: formatCount(state.counts.customers, lang),
      scans: formatCount(state.counts.tracking_scans, lang),
      hubs: formatCount(state.counts.hubs, lang),
      days: days.length,
    }),
    t(lang, "detection", {
      failingChecks: failingChecks.length,
      failingDays: failingDays.length,
      days: days.length,
      precision: evaluation.precision.toFixed(3),
      recall: evaluation.recall.toFixed(3),
      rowCaught: evaluation.row_level_caught,
      rowApplicable: evaluation.row_level_applicable,
    }),
  ];
  const selected = state.filters.date === "all" ? null : days.find((day) => day.business_date === state.filters.date);
  if (selected) {
    sentences.push(
      t(lang, "selected", {
        date: formatDay(selected.business_date, lang),
        score: formatScore(selected.score),
        sla: statusLabel(selected.status, lang),
        failedText:
          selected.checks_failed === 1
            ? t(lang, "oneFail")
            : t(lang, "manyFail", { failed: selected.checks_failed }),
      }),
    );
  } else if (days.length) {
    const lowest = [...days].sort((a, b) => a.score - b.score)[0];
    sentences.push(t(lang, "lowest", { score: formatScore(lowest.score), date: formatDay(lowest.business_date, lang) }));
    const soft = days.find((day) => day.status === "pass" && day.checks_failed > 0);
    if (soft) {
      sentences.push(
        t(lang, "passWithFail", {
          date: formatDay(soft.business_date, lang),
          score: formatScore(soft.score),
          failed: soft.checks_failed,
        }),
      );
    }
  }
  const focus = selected || days.find((day) => day.status === "fail" && day.critical_failed > 0 && day.score + 1e-9 >= Number(state.suite.pass_score));
  const late = focus
    ? state.results.find((row) => row.business_date === focus.business_date && row.check_type === "freshness" && row.status === "fail")
    : null;
  if (late) {
    sentences.push(
      t(lang, "late", {
        table: late.table_name,
        hours: Number(late.metric_value).toFixed(2),
        loaded: late.detail.loaded,
        deadline: late.detail.deadline,
      }),
    );
  } else if (focus && !selected && focus.status === "fail" && focus.score + 1e-9 >= Number(state.suite.pass_score)) {
    sentences.push(
      t(lang, "aboveLine", {
        date: formatDay(focus.business_date, lang),
        score: formatScore(focus.score),
        line: Number(state.suite.pass_score),
      }),
    );
  }
  const drifted = TABLES.filter((table) => state.counts[table] !== state.manifest.counts[table]);
  if (drifted.length) sentences.push(t(lang, "mismatch", { tables: drifted.join(", ") }));
  return sentences;
}

function paintChrome() {
  const lang = state.lang;
  document.documentElement.lang = lang;
  document.title = t(lang, "docTitle");
  document.querySelector(".skip").textContent = t(lang, "skip");
  document.querySelector(".mark").textContent = t(lang, "mark");
  document.querySelector(".mark-sub").textContent = t(lang, "markSub");
  document.querySelector("#title").textContent = t(lang, "title");
  const langGroup = document.querySelector("#lang");
  clear(langGroup);
  langGroup.setAttribute("aria-label", t(lang, "langLabel"));
  for (const code of ["es", "en"]) {
    langGroup.append(
      el("button", {
        type: "button",
        class: code === lang ? "lang is-on" : "lang",
        "aria-pressed": code === lang ? "true" : "false",
        text: code.toUpperCase(),
        onClick: () => {
          state.lang = code;
          localStorage.setItem("rutanorte-lang", code);
          paint();
        },
      }),
    );
  }
  document.querySelector("[data-profile]").textContent = t(lang, "profile");
  document.querySelector("[data-repo]").textContent = t(lang, "repo");
  document.querySelector("[data-profile-foot]").textContent = t(lang, "profile");
  document.querySelector("[data-repo-foot]").textContent = t(lang, "repo");
  document.querySelector("[data-colophon]").textContent = t(lang, "colophon");
  document.querySelector("[data-local]").textContent = t(lang, "local");
  document.querySelector("[data-synthetic]").textContent = t(lang, "synthetic");
}

function paintRules() {
  const lang = state.lang;
  const root = document.querySelector("#rules");
  clear(root);
  const line = state.suite ? Number(state.suite.pass_score) : 95;
  root.append(
    el("h2", { text: t(lang, "rulesTitle") }),
    el("p", { text: t(lang, "rulesScore") }),
    el("p", { text: t(lang, "rulesSla", { line }) }),
    el("p", { text: t(lang, "rulesDrift") }),
    el("p", { text: t(lang, "rulesId") }),
    el("p", { text: t(lang, "rulesData") }),
  );
}

function paint() {
  motionToken += 1;
  paintChrome();
  paintRules();
  const lede = document.querySelector("#lede");
  const progressRow = document.querySelector("#progress-row");
  const trend = document.querySelector("#trend");
  const filters = document.querySelector("#filters");
  const tabs = document.querySelector("#tabs");
  const panels = document.querySelector("#panels");
  if (state.error) {
    progressRow.hidden = true;
    trend.hidden = true;
    filters.hidden = true;
    tabs.hidden = true;
    panels.hidden = true;
    clear(lede);
    lede.append(el("strong", { text: t(state.lang, "errorTitle") }), ` ${state.error.message}`);
    return;
  }
  if (!state.ready) {
    progressRow.hidden = false;
    trend.hidden = true;
    filters.hidden = true;
    tabs.hidden = true;
    panels.hidden = true;
    lede.textContent = t(state.lang, "loading");
    setProgress(state.progress.value, state.progress.max, state.progress.label || t(state.lang, "loading"));
    return;
  }
  progressRow.hidden = true;
  trend.hidden = false;
  filters.hidden = false;
  tabs.hidden = false;
  panels.hidden = false;
  clear(lede);
  const sentences = ledeSentences();
  sentences.forEach((sentence, index) => {
    const node = el("span", { class: "sentence", text: sentence });
    if (index === 1) {
      const failing = state.results.filter((row) => row.status === "fail").length;
      node.dataset.count = String(failing);
      node.dataset.decimals = "0";
    }
    lede.append(node);
  });
  lede.append(
    el("span", {
      class: "source",
      text: t(state.lang, "source", { seconds: (state.elapsedMs / 1000).toFixed(1) }),
    }),
  );
  renderTrend();
  renderFilters();
  renderTabs();
  renderPanels();
}

function renderTrend() {
  const lang = state.lang;
  const days = dayScores();
  const figure = document.querySelector("#trend");
  clear(figure);
  const width = 920;
  const height = 214;
  const pad = { l: 40, r: 16, t: 18, b: 32 };
  const minY = 74;
  const maxY = 100;
  const xAt = (index) => pad.l + (index * (width - pad.l - pad.r)) / Math.max(days.length - 1, 1);
  const yAt = (score) => pad.t + ((maxY - score) / (maxY - minY)) * (height - pad.t - pad.b);
  const failing = days.filter((day) => day.status === "fail").map((day) => formatDay(day.business_date, lang));
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("class", "trend-svg");
  const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
  title.textContent = t(lang, "trendTitle");
  const desc = document.createElementNS("http://www.w3.org/2000/svg", "desc");
  desc.textContent = `${formatDay(days[0].business_date, lang)} a ${formatDay(days.at(-1).business_date, lang)}. SLA ${state.suite.pass_score}. ${failing.join(", ")}`;
  svg.append(title, desc);
  const axis = document.createElementNS("http://www.w3.org/2000/svg", "g");
  for (const tick of [80, 90, 100]) {
    const y = yAt(tick);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", pad.l);
    line.setAttribute("x2", width - pad.r);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("class", "grid");
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", pad.l - 8);
    label.setAttribute("y", y + 4);
    label.setAttribute("text-anchor", "end");
    label.setAttribute("class", "tick");
    label.textContent = String(tick);
    axis.append(line, label);
  }
  const slaY = yAt(Number(state.suite.pass_score));
  const sla = document.createElementNS("http://www.w3.org/2000/svg", "line");
  sla.setAttribute("x1", pad.l);
  sla.setAttribute("x2", width - pad.r);
  sla.setAttribute("y1", slaY);
  sla.setAttribute("y2", slaY);
  sla.setAttribute("class", "sla");
  const slaLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
  slaLabel.setAttribute("x", pad.l + 6);
  slaLabel.setAttribute("y", slaY - 6);
  slaLabel.setAttribute("text-anchor", "start");
  slaLabel.setAttribute("class", "sla-label");
  slaLabel.textContent = `SLA ${Number(state.suite.pass_score)}`;
  const points = days.map((day, index) => `${xAt(index)},${yAt(day.score)}`).join(" ");
  const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  poly.setAttribute("points", points);
  poly.setAttribute("class", "trend-line");
  svg.append(axis, sla, slaLabel, poly);
  days.forEach((day, index) => {
    const selected = state.filters.date === day.business_date;
    const shape = day.status === "fail" ? "square" : day.checks_failed > 0 ? "diamond" : "circle";
    const cx = xAt(index);
    const cy = yAt(day.score);
    const node = document.createElementNS("http://www.w3.org/2000/svg", shape === "circle" ? "circle" : "polygon");
    if (shape === "circle") {
      node.setAttribute("cx", cx);
      node.setAttribute("cy", cy);
      node.setAttribute("r", selected ? 6 : 4);
    } else if (shape === "square") {
      const s = selected ? 6 : 4.5;
      node.setAttribute("points", `${cx - s},${cy - s} ${cx + s},${cy - s} ${cx + s},${cy + s} ${cx - s},${cy + s}`);
    } else {
      const s = selected ? 7 : 5.5;
      node.setAttribute("points", `${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}`);
    }
    node.setAttribute("class", `point ${shape}${selected ? " is-selected" : ""}`);
    const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
    tip.textContent = `${formatDay(day.business_date, lang)} ${formatScore(day.score)} ${statusLabel(day.status, lang)}`;
    node.append(tip);
    node.addEventListener("click", () => {
      state.filters.date = state.filters.date === day.business_date ? "all" : day.business_date;
      state.selectedKey = null;
      paint();
    });
    svg.append(node);
  });
  for (const index of [0, 14, 30, days.length - 1]) {
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", xAt(index));
    label.setAttribute("y", height - 8);
    label.setAttribute("text-anchor", index === 0 ? "start" : index === days.length - 1 ? "end" : "middle");
    label.setAttribute("class", "tick");
    label.textContent = days[index].business_date.slice(5);
    svg.append(label);
  }
  figure.append(svg, el("figcaption", { text: t(lang, "trendHint") }));
  if (!reduceMotion) {
    requestAnimationFrame(() => {
      const length = poly.getTotalLength?.() || 1000;
      poly.style.setProperty("--length", `${length}`);
      poly.classList.add("draw");
    });
  }
}

function renderFilters() {
  const lang = state.lang;
  const form = document.querySelector("#filters");
  clear(form);
  form.addEventListener("submit", (event) => event.preventDefault());
  const days = dayScores();
  form.append(
    field(t(lang, "filterDate"), "date", [
      [ "all", t(lang, "allDates") ],
      ...days.map((day) => [day.business_date, `${day.business_date} ${statusLabel(day.status, lang)}`]),
    ]),
    field(t(lang, "filterTable"), "table", [
      ["all", t(lang, "allTables")],
      ...TABLES.map((table) => [table, table]),
    ]),
    field(t(lang, "filterSeverity"), "severity", [
      ["all", t(lang, "allSeverities")],
      ...["critical", "high", "medium", "low"].map((item) => [item, severityLabel(item, lang)]),
    ]),
    field(t(lang, "filterStatus"), "status", [
      ["all", t(lang, "allStatuses")],
      ...["fail", "pass", "skipped"].map((item) => [item, statusLabel(item, lang)]),
    ]),
    el("p", { class: "filter-note", text: t(lang, "filterNote") }),
  );
}

function field(label, key, options) {
  const select = el("select", { id: `filter-${key}` });
  for (const [value, text] of options) {
    const option = el("option", { value, text });
    if (value === state.filters[key]) option.selected = true;
    select.append(option);
  }
  select.addEventListener("change", () => {
    state.filters[key] = select.value;
    state.selectedKey = null;
    paint();
  });
  return el("label", {}, [label, select]);
}

function renderTabs() {
  const lang = state.lang;
  const root = document.querySelector("#tabs");
  clear(root);
  root.setAttribute("role", "tablist");
  root.setAttribute("aria-label", t(lang, "title"));
  for (const id of ["checks", "incidents", "lineage", "sql"]) {
    root.append(
      el("button", {
        type: "button",
        role: "tab",
        id: `tab-${id}`,
        "aria-selected": state.tab === id ? "true" : "false",
        "aria-controls": `panel-${id}`,
        tabindex: state.tab === id ? "0" : "-1",
        text: t(lang, `tab${id[0].toUpperCase()}${id.slice(1)}`),
        onClick: () => {
          state.tab = id;
          renderTabs();
          renderPanels();
        },
      }),
    );
  }
}

function renderPanels() {
  const root = document.querySelector("#panels");
  clear(root);
  root.append(renderChecks(), renderIncidents(), renderLineage(), renderSql());
}

function renderChecks() {
  const lang = state.lang;
  const rows = visibleChecks();
  const panel = el("section", {
    id: "panel-checks",
    role: "tabpanel",
    "aria-labelledby": "tab-checks",
    hidden: state.tab === "checks" ? null : "hidden",
  });
  panel.append(el("p", { class: "caption", text: t(lang, "checksCaption", { shown: rows.length, total: state.results.length }) }));
  if (!rows.length) {
    panel.append(el("p", { text: t(lang, "emptyChecks") }));
    return panel;
  }
  const table = el("table");
  table.append(
    el("thead", {}, [
      el("tr", {}, ["colDate", "colCheck", "colTable", "colSeverity", "colStatus", "colMetric", "colRows"].map((key) => el("th", { scope: "col", text: t(lang, key) }))),
    ]),
  );
  const body = el("tbody");
  for (const row of rows) {
    const key = resultKey(row);
    const selected = state.selectedKey === key;
    const tr = el("tr", {
      tabindex: "0",
      "aria-pressed": selected ? "true" : "false",
      class: selected ? "is-selected" : "",
    });
    const open = () => {
      state.selectedKey = state.selectedKey === key ? null : key;
      renderPanels();
    };
    tr.addEventListener("click", open);
    tr.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
    tr.append(
      el("td", { text: row.business_date }),
      el("td", { class: "mono", text: row.check_id }),
      el("td", { class: "mono", text: row.table_name }),
      el("td", { text: severityLabel(row.severity, lang) }),
      el("td", { class: row.status === "fail" ? "fail" : "", text: statusLabel(row.status, lang) }),
      el("td", { text: metricCell(row, lang) }),
      el("td", { text: t(lang, "rowsPair", { failed: row.failed_row_count, total: row.total_row_count }) }),
    );
    body.append(tr);
  }
  table.append(body);
  panel.append(el("div", { class: "table-scroll" }, [table]));
  const selected = rows.find((row) => resultKey(row) === state.selectedKey);
  if (selected) panel.append(renderDetail(selected));
  return panel;
}

function renderDetail(row) {
  const lang = state.lang;
  const section = el("section", { class: "detail", "aria-live": "polite" });
  section.append(
    el("h2", { class: "mono detail-id", text: row.check_id }),
    el("p", { text: describe(row, lang) }),
    el("p", { text: checkDescription(row.check_id, row.description, lang) }),
  );
  if (!row.samples?.length) {
    section.append(el("p", { class: "caption", text: t(lang, "noSamples") }));
    return section;
  }
  section.append(el("h3", { text: t(lang, "samples") }));
  section.append(sampleTable(row.samples));
  return section;
}

function sampleTable(samples) {
  const keys = [];
  for (const sample of samples) {
    for (const key of Object.keys(sample)) if (!keys.includes(key)) keys.push(key);
  }
  const table = el("table");
  table.append(el("thead", {}, [el("tr", {}, keys.map((key) => el("th", { scope: "col", class: "mono", text: key })))]));
  const body = el("tbody");
  for (const sample of samples) {
    body.append(
      el(
        "tr",
        {},
        keys.map((key) => {
          const value = sample[key];
          const text = value == null ? "null" : typeof value === "number" ? formatSampleNumber(key, value) : String(value);
          return el("td", { class: value == null ? "mono null" : "mono", text });
        }),
      ),
    );
  }
  table.append(body);
  return el("div", { class: "table-scroll" }, [table]);
}

function formatSampleNumber(key, value) {
  if (key.endsWith("share")) return `${(value * 100).toFixed(2)}%`;
  if (Number.isInteger(value)) return String(value);
  return String(Math.round(value * 10000) / 10000);
}

function renderIncidents() {
  const lang = state.lang;
  const rows = visibleDefects();
  const caught = state.defects.filter((defect) => defectCaught(defect).caught).length;
  const panel = el("section", {
    id: "panel-incidents",
    role: "tabpanel",
    "aria-labelledby": "tab-incidents",
    hidden: state.tab === "incidents" ? null : "hidden",
  });
  panel.append(
    el("p", {
      class: "caption",
      text: t(lang, "incidentsCaption", { caught, total: state.defects.length }),
    }),
  );
  if (!rows.length) {
    panel.append(el("p", { text: t(lang, "emptyIncidents") }));
    return panel;
  }
  const table = el("table");
  table.append(
    el("thead", {}, [
      el("tr", {}, ["colDate", "colDefect", "colCheck", "colTable", "colObserved", "colMinimum", "colResult"].map((key) => el("th", { scope: "col", text: t(lang, key) }))),
    ]),
  );
  const body = el("tbody");
  for (const defect of rows) {
    const outcome = defectCaught(defect);
    body.append(
      el("tr", {}, [
        el("td", { text: defect.business_date }),
        el("td", {}, [
          el("div", { class: "mono", text: defect.id }),
          el("div", { text: defectDescription(defect.id, defect.description, lang) }),
        ]),
        el("td", { class: "mono", text: defect.check_id }),
        el("td", { class: "mono", text: defect.table }),
        el("td", { text: outcome.observed == null ? "" : String(outcome.observed) }),
        el("td", { text: defect.min_failed_rows == null ? "" : String(defect.min_failed_rows) }),
        el("td", { class: outcome.caught ? "" : "fail", text: t(lang, outcome.caught ? "caught" : "missed") }),
      ]),
    );
  }
  table.append(body);
  panel.append(el("div", { class: "table-scroll" }, [table]));
  return panel;
}

function edgePath(from, to, edgeIndex) {
  const y1 = from.y + from.h / 2;
  const y2 = to.y + to.h / 2;
  if (Math.abs(from.x - to.x) > 40) {
    const x1 = from.x + from.w;
    const x2 = to.x;
    const mid = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`;
  }
  const x = from.x + from.w + 18 + (edgeIndex % 3) * 10;
  return `M ${from.x + from.w} ${y1} H ${x} V ${y2} H ${to.x + to.w}`;
}

function renderLineage() {
  const lang = state.lang;
  const panel = el("section", {
    id: "panel-lineage",
    role: "tabpanel",
    "aria-labelledby": "tab-lineage",
    hidden: state.tab === "lineage" ? null : "hidden",
  });
  panel.append(el("p", { text: t(lang, "lineageIntro") }));
  const nodes = state.suite.nodes;
  const order = [
    "raw_customer_signups",
    "raw_hub_registry",
    "raw_shipment_events",
    "raw_scan_events",
    "customers",
    "hubs",
    "shipments",
    "tracking_scans",
    "daily_route_kpis",
  ];
  const layers = ["extract", "warehouse", "mart"];
  const xFor = { extract: 16, warehouse: 330, mart: 644 };
  const positions = {};
  for (const layer of layers) {
    nodes
      .filter((node) => node.layer === layer)
      .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))
      .forEach((node, index) => {
        const y = layer === "mart" && positions.shipments ? positions.shipments.y : 20 + index * 84;
        positions[node.id] = { x: xFor[layer], y, w: 230, h: 62 };
      });
  }
  const height = 20 + 4 * 84 + 24;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 900 ${height}`);
  svg.setAttribute("class", "lineage");
  svg.setAttribute("role", "img");
  const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
  title.textContent = t(lang, "tabLineage");
  svg.append(title);
  state.suite.lineage.forEach((edge, edgeIndex) => {
    const from = positions[edge.from];
    const to = positions[edge.to];
    if (!from || !to) return;
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", edgePath(from, to, edgeIndex));
    path.setAttribute("class", "edge");
    svg.append(path);
  });
  for (const node of nodes) {
    const box = positions[node.id];
    const status = nodeStatus(node);
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", box.x);
    rect.setAttribute("y", box.y);
    rect.setAttribute("width", box.w);
    rect.setAttribute("height", box.h);
    rect.setAttribute("rx", "2");
    rect.setAttribute("class", `node${status.fail ? " is-fail" : ""}${state.filters.table === node.id ? " is-focus" : ""}`);
    const name = document.createElementNS("http://www.w3.org/2000/svg", "text");
    name.setAttribute("x", box.x + 12);
    name.setAttribute("y", box.y + 26);
    name.setAttribute("class", "node-name");
    name.textContent = nodeLabel(node, lang);
    const meta = document.createElementNS("http://www.w3.org/2000/svg", "text");
    meta.setAttribute("x", box.x + 12);
    meta.setAttribute("y", box.y + 46);
    meta.setAttribute("class", status.fail ? "node-meta fail" : "node-meta");
    meta.textContent = status.text;
    group.append(rect, name, meta);
    svg.append(group);
  }
  panel.append(svg);
  const mermaid = ["flowchart LR"];
  for (const edge of state.suite.lineage) mermaid.push(`  ${edge.from} --> ${edge.to}`);
  const pre = el("pre", { class: "mono", text: mermaid.join("\n") });
  panel.append(el("details", {}, [el("summary", { text: t(lang, "mermaidSummary") }), pre]));
  return panel;
}

function nodeStatus(node) {
  const lang = state.lang;
  if (node.layer === "extract") return { fail: false, text: t(lang, "declared") };
  const rows = state.scores.filter((score) => score.table_name === node.id);
  const scoped = state.filters.date === "all" ? rows : rows.filter((score) => score.business_date === state.filters.date);
  if (!scoped.length) return { fail: false, text: "" };
  if (state.filters.date !== "all") {
    const score = scoped[0];
    return { fail: score.status === "fail" || score.checks_failed > 0, text: `${formatScore(score.score)} ${statusLabel(score.status, lang)}` };
  }
  const failCount = scoped.filter((score) => score.checks_failed > 0).length;
  if (failCount) return { fail: true, text: t(lang, "failDays", { count: failCount }) };
  return { fail: false, text: t(lang, "cleanDays") };
}

function renderSql() {
  const lang = state.lang;
  const panel = el("section", {
    id: "panel-sql",
    role: "tabpanel",
    "aria-labelledby": "tab-sql",
    hidden: state.tab === "sql" ? null : "hidden",
  });
  panel.append(el("p", { text: t(lang, "sqlIntro") }));
  const presets = el("div", { class: "presets" });
  for (const [key, labelKey] of [
    ["channel", "presetChannel"],
    ["email", "presetEmail"],
    ["late", "presetLate"],
  ]) {
    presets.append(
      el("button", {
        type: "button",
        text: t(lang, labelKey),
        onClick: () => {
          state.sql = SQL_PRESETS[key];
          state.sqlError = null;
          runQuery();
        },
      }),
    );
  }
  const area = el("textarea", { id: "sql", spellcheck: "false" });
  area.value = state.sql;
  area.addEventListener("input", () => {
    state.sql = area.value;
  });
  const button = el("button", {
    type: "button",
    class: "primary",
    text: t(lang, "sqlRun"),
    onClick: () => runQuery(),
  });
  panel.append(presets, area, button, el("div", { id: "sql-result" }));
  paintSqlResult();
  return panel;
}

async function runQuery() {
  state.sqlError = null;
  state.sqlRows = null;
  try {
    const sql = guardSelect(state.sql);
    const wrapped = `SELECT * FROM (${sql}) AS user_query LIMIT ${SQL_CAP + 1}`;
    const rows = rowsFrom(await state.connection.query(wrapped));
    state.sqlTruncated = rows.length > SQL_CAP;
    state.sqlRows = rows.slice(0, SQL_CAP);
    state.sqlColumns = state.sqlRows.length ? Object.keys(state.sqlRows[0]) : [];
  } catch (error) {
    const known = { empty: "errEmpty", multi: "errMulti", "not-select": "errSelect", forbidden: "errForbidden" };
    state.sqlError = known[error.message] ? t(state.lang, known[error.message]) : t(state.lang, "errSql", { message: error.message });
    state.sqlRows = null;
  }
  paintSqlResult();
}

function paintSqlResult() {
  const lang = state.lang;
  const root = document.querySelector("#sql-result");
  if (!root) return;
  clear(root);
  if (state.sqlError) {
    root.append(el("p", { class: "fail", role: "alert", text: state.sqlError }));
    return;
  }
  if (!state.sqlRows) return;
  if (!state.sqlRows.length) {
    root.append(el("p", { text: t(lang, "sqlEmpty") }));
    return;
  }
  root.append(
    el("p", {
      class: "caption",
      text: state.sqlTruncated ? t(lang, "sqlTruncated", { shown: state.sqlRows.length }) : t(lang, "sqlRows", { shown: state.sqlRows.length }),
    }),
  );
  root.append(sampleTable(state.sqlRows));
}

paint();
boot();
