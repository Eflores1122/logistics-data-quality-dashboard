/**
 * Browser port of the RutaNorte check engine.
 *
 * The SQL and the scoring rules follow src/rutanorte_dq/engine.py,
 * scoring.py, and evaluate.py. scripts/verify_browser_engine.mjs compares
 * a full run with the Python reference output.
 */

import { binEdges, deviationFromMedian, expandPairs, histogram, psi } from "./metrics.js";

const IDENT = /^[A-Za-z_][A-Za-z0-9_]*$/;
const METRIC = /^(count\(\*\)|sum\([A-Za-z_][A-Za-z0-9_]*\))$/;
const DAY_TABLE = "__day__";
const SAMPLE_LIMIT = 15;

export { DAY_TABLE };

export function quoteIdent(name) {
  if (typeof name !== "string" || !IDENT.test(name)) {
    throw new Error(`Refusing unsafe SQL identifier: ${name}`);
  }
  return `"${name}"`;
}

function dateLiteral(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) throw new Error(`Bad business date: ${iso}`);
  return `DATE '${iso}'`;
}

function sqlString(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function num(value) {
  if (typeof value === "bigint") return Number(value);
  return Number(value);
}

function asDate(value) {
  if (value == null) return null;
  return String(value).slice(0, 10);
}

function round4(value) {
  const sign = value < 0 ? -1 : 1;
  const scaled = Math.abs(value) * 10000;
  const floor = Math.floor(scaled + 1e-8);
  const frac = scaled - floor;
  let rounded;
  if (frac > 0.5 + 1e-8) rounded = floor + 1;
  else if (frac < 0.5 - 1e-8) rounded = floor;
  else rounded = floor % 2 === 0 ? floor : floor + 1;
  return (sign * rounded) / 10000;
}

function result(table, check, businessDate, fields) {
  return {
    business_date: businessDate,
    table_name: table.name,
    check_id: check.id,
    check_type: check.type,
    severity: check.severity,
    description: check.description,
    column: check.column || (check.columns || []).join(", ") || null,
    status: fields.status,
    metric_name: fields.metric_name,
    metric_value: fields.metric_value,
    threshold: fields.threshold,
    comparator: fields.comparator,
    failed_row_count: fields.failed_row_count,
    total_row_count: fields.total_row_count,
    samples: fields.samples || [],
    detail: fields.detail || {},
  };
}

function validityPredicate(format, column) {
  const raw = `trim(CAST(${column} AS VARCHAR))`;
  const upper = `upper(${raw})`;
  if (format === "email") {
    return `regexp_full_match(${raw}, '^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$')`;
  }
  if (format === "phone_mx") {
    return `regexp_full_match(${raw}, '^\\+52[2-9][0-9]{9}$')`;
  }
  if (format === "rfc_fisica") {
    return (
      `regexp_full_match(${upper}, '^[A-ZÑ&]{4}[0-9]{6}[A-Z0-9]{3}$') ` +
      `AND try_strptime(substr(${upper}, 5, 6), '%y%m%d') IS NOT NULL`
    );
  }
  if (format === "rfc_moral") {
    return (
      `regexp_full_match(${upper}, '^[A-ZÑ&]{3}[0-9]{6}[A-Z0-9]{3}$') ` +
      `AND try_strptime(substr(${upper}, 4, 6), '%y%m%d') IS NOT NULL`
    );
  }
  if (format === "curp") {
    return (
      `regexp_full_match(${upper}, '^[A-Z][AEIOUX][A-Z]{2}[0-9]{6}[HM]` +
      `(AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)` +
      `[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9][0-9]$') ` +
      `AND try_strptime(substr(${upper}, 5, 6), '%y%m%d') IS NOT NULL`
    );
  }
  throw new Error(`Unknown format ${format}`);
}

async function sampleRows(query, sql) {
  const rows = await query(sql);
  return rows.map((row) => {
    const payload = row.row_json;
    return typeof payload === "string" ? JSON.parse(payload) : payload;
  });
}

function sampleSelect(tableName, whereSql, orderCol) {
  const where = whereSql ? `WHERE ${whereSql}` : "";
  const order = orderCol ? `ORDER BY ${orderCol}` : "";
  return `
    SELECT CAST(to_json(src) AS VARCHAR) AS row_json
    FROM ${tableName} AS src
    ${where}
    ${order}
    LIMIT ${SAMPLE_LIMIT}
  `;
}

async function grouped(query, table, check, selectSql) {
  const source = quoteIdent(table.name);
  if (check.scope === "table") {
    const rows = await query(`SELECT ${selectSql} FROM ${source}`);
    return rows.map((row) => ({ ...row, business_date: null }));
  }
  const dateCol = quoteIdent(table.business_date_column);
  return query(`
    SELECT CAST(${dateCol} AS VARCHAR) AS business_date, ${selectSql}
    FROM ${source}
    GROUP BY ${dateCol}
    ORDER BY ${dateCol}
  `);
}

async function completeness(query, suite, table, check) {
  const column = quoteIdent(check.column);
  const blank = `(${column} IS NULL OR length(trim(CAST(${column} AS VARCHAR))) = 0)`;
  const threshold = check.max_null_rate == null ? 0 : Number(check.max_null_rate);
  const rows = await grouped(
    query,
    table,
    check,
    `count(*)::DOUBLE AS total, count(*) FILTER (WHERE ${blank})::DOUBLE AS failed`,
  );
  const output = [];
  for (const row of rows) {
    const total = Math.round(num(row.total));
    const failed = Math.round(num(row.failed));
    const when = row.business_date ? asDate(row.business_date) : suite.as_of;
    const rate = total ? failed / total : 0;
    const status = rate > threshold + 1e-12 ? "fail" : "pass";
    let samples = [];
    if (status === "fail") {
      const dateSql =
        check.scope === "partition"
          ? `${quoteIdent(table.business_date_column)} = ${dateLiteral(when)} AND `
          : "";
      const order = table.key ? quoteIdent(table.key) : "";
      samples = await sampleRows(
        query,
        sampleSelect(quoteIdent(table.name), `${dateSql}${blank}`, order),
      );
    }
    output.push(
      result(table, check, when, {
        status,
        metric_name: "null_rate",
        metric_value: rate,
        threshold,
        comparator: "<=",
        failed_row_count: status === "fail" ? failed : 0,
        total_row_count: total,
        samples,
        detail: { failed, total, rate, threshold },
      }),
    );
  }
  return output;
}

async function uniqueness(query, suite, table, check) {
  const columns = check.columns?.length ? check.columns : check.column ? [check.column] : [];
  if (!columns.length) throw new Error(`${check.id} requires columns`);
  const quoted = columns.map(quoteIdent);
  const source = quoteIdent(table.name);
  let measured;
  if (check.scope === "table") {
    const sql = `
      WITH grouped AS (
        SELECT ${quoted.join(", ")}, count(*) AS c
        FROM ${source}
        GROUP BY ${quoted.join(", ")}
      )
      SELECT coalesce(sum(c), 0)::DOUBLE AS total,
             coalesce(sum(CASE WHEN c > 1 THEN c ELSE 0 END), 0)::DOUBLE AS failed
      FROM grouped
    `;
    const row = (await query(sql))[0];
    measured = [{ business_date: suite.as_of, total: Math.round(num(row.total)), failed: Math.round(num(row.failed)) }];
  } else {
    const dateCol = quoteIdent(table.business_date_column);
    const sql = `
      WITH grouped AS (
        SELECT ${dateCol} AS business_date, ${quoted.join(", ")}, count(*) AS c
        FROM ${source}
        GROUP BY ${dateCol}, ${quoted.join(", ")}
      )
      SELECT CAST(business_date AS VARCHAR) AS business_date,
             coalesce(sum(c), 0)::DOUBLE AS total,
             coalesce(sum(CASE WHEN c > 1 THEN c ELSE 0 END), 0)::DOUBLE AS failed
      FROM grouped
      GROUP BY business_date
      ORDER BY business_date
    `;
    measured = (await query(sql)).map((row) => ({
      business_date: asDate(row.business_date),
      total: Math.round(num(row.total)),
      failed: Math.round(num(row.failed)),
    }));
  }
  const output = [];
  for (const row of measured) {
    const status = row.failed ? "fail" : "pass";
    let samples = [];
    if (status === "fail") samples = await duplicateSamples(query, table, check, row.business_date, columns);
    output.push(
      result(table, check, row.business_date, {
        status,
        metric_name: "duplicate_rows",
        metric_value: row.failed,
        threshold: 0,
        comparator: "==",
        failed_row_count: row.failed,
        total_row_count: row.total,
        samples,
        detail: { failed: row.failed, total: row.total, columns: columns.join(", ") },
      }),
    );
  }
  return output;
}

async function duplicateSamples(query, table, check, businessDate, columns) {
  const quoted = columns.map(quoteIdent);
  const source = quoteIdent(table.name);
  const dateFilter =
    check.scope === "partition"
      ? `WHERE ${quoteIdent(table.business_date_column)} = ${dateLiteral(businessDate)}`
      : "";
  const srcDate =
    check.scope === "partition"
      ? `WHERE src.${quoteIdent(table.business_date_column)} = ${dateLiteral(businessDate)}`
      : "";
  const joinOn = quoted.map((column) => `src.${column} = dup.${column}`).join(" AND ");
  const sql = `
    WITH dup AS (
      SELECT ${quoted.join(", ")}
      FROM ${source}
      ${dateFilter}
      GROUP BY ${quoted.join(", ")}
      HAVING count(*) > 1
    )
    SELECT CAST(to_json(src) AS VARCHAR) AS row_json
    FROM ${source} AS src
    JOIN dup ON ${joinOn}
    ${srcDate}
    LIMIT ${SAMPLE_LIMIT}
  `;
  return sampleRows(query, sql);
}

async function validity(query, suite, table, check) {
  const column = quoteIdent(check.column);
  const present = `${column} IS NOT NULL AND length(trim(CAST(${column} AS VARCHAR))) > 0`;
  const invalid = `${present} AND NOT (${validityPredicate(check.format, column)})`;
  const threshold = check.max_invalid_rate == null ? 0 : Number(check.max_invalid_rate);
  const rows = await grouped(
    query,
    table,
    check,
    `count(*)::DOUBLE AS total,
     count(*) FILTER (WHERE ${invalid})::DOUBLE AS failed,
     count(*) FILTER (WHERE ${present})::DOUBLE AS present`,
  );
  const output = [];
  for (const row of rows) {
    const total = Math.round(num(row.total));
    const failed = Math.round(num(row.failed));
    const presentCount = Math.round(num(row.present));
    const when = row.business_date ? asDate(row.business_date) : suite.as_of;
    const rate = presentCount ? failed / presentCount : 0;
    const status = rate > threshold + 1e-12 ? "fail" : "pass";
    let samples = [];
    if (status === "fail") {
      const dateSql =
        check.scope === "partition"
          ? `${quoteIdent(table.business_date_column)} = ${dateLiteral(when)} AND `
          : "";
      const order = table.key ? quoteIdent(table.key) : "";
      samples = await sampleRows(
        query,
        sampleSelect(quoteIdent(table.name), `${dateSql}(${invalid})`, order),
      );
    }
    output.push(
      result(table, check, when, {
        status,
        metric_name: "invalid_rate",
        metric_value: rate,
        threshold,
        comparator: "<=",
        failed_row_count: status === "fail" ? failed : 0,
        total_row_count: total,
        samples,
        detail: { failed, present: presentCount, total, rate, threshold, format: check.format },
      }),
    );
  }
  return output;
}

async function acceptedValues(query, suite, table, check) {
  if (!check.values?.length) throw new Error(`${check.id} requires values`);
  const column = quoteIdent(check.column);
  const list = check.values.map(sqlString).join(", ");
  const rejected = `(${column} IS NULL OR CAST(${column} AS VARCHAR) NOT IN (${list}))`;
  const rows = await grouped(
    query,
    table,
    check,
    `count(*)::DOUBLE AS total, count(*) FILTER (WHERE ${rejected})::DOUBLE AS failed`,
  );
  const output = [];
  for (const row of rows) {
    const total = Math.round(num(row.total));
    const failed = Math.round(num(row.failed));
    const when = row.business_date ? asDate(row.business_date) : suite.as_of;
    const status = failed ? "fail" : "pass";
    let samples = [];
    if (status === "fail") {
      const dateSql =
        check.scope === "partition"
          ? `${quoteIdent(table.business_date_column)} = ${dateLiteral(when)} AND `
          : "";
      const order = table.key ? quoteIdent(table.key) : "";
      samples = await sampleRows(
        query,
        sampleSelect(quoteIdent(table.name), `${dateSql}${rejected}`, order),
      );
    }
    output.push(
      result(table, check, when, {
        status,
        metric_name: "rejected_rows",
        metric_value: failed,
        threshold: 0,
        comparator: "==",
        failed_row_count: failed,
        total_row_count: total,
        samples,
        detail: { failed, total, allowed: check.values.join(", ") },
      }),
    );
  }
  return output;
}

async function referential(query, suite, table, check) {
  if (!check.references_table || !check.references_column || !check.column) {
    throw new Error(`${check.id} requires column and references`);
  }
  const child = quoteIdent(check.column);
  const parentTable = quoteIdent(check.references_table);
  const parentColumn = quoteIdent(check.references_column);
  const source = quoteIdent(table.name);
  const join = `
    LEFT JOIN (SELECT DISTINCT ${parentColumn} FROM ${parentTable}) AS parent
      ON src.${child} = parent.${parentColumn}
  `;
  const failedSql = `count(*) FILTER (WHERE parent.${parentColumn} IS NULL)::DOUBLE AS failed`;
  let measured;
  if (check.scope === "table") {
    const row = (
      await query(`SELECT count(*)::DOUBLE AS total, ${failedSql} FROM ${source} AS src ${join}`)
    )[0];
    measured = [{ business_date: suite.as_of, total: Math.round(num(row.total)), failed: Math.round(num(row.failed)) }];
  } else {
    const dateCol = quoteIdent(table.business_date_column);
    const rows = await query(`
      SELECT CAST(src.${dateCol} AS VARCHAR) AS business_date,
             count(*)::DOUBLE AS total,
             ${failedSql}
      FROM ${source} AS src
      ${join}
      GROUP BY src.${dateCol}
      ORDER BY src.${dateCol}
    `);
    measured = rows.map((row) => ({
      business_date: asDate(row.business_date),
      total: Math.round(num(row.total)),
      failed: Math.round(num(row.failed)),
    }));
  }
  const output = [];
  for (const row of measured) {
    const status = row.failed ? "fail" : "pass";
    let samples = [];
    if (status === "fail") {
      const dateSql =
        check.scope === "partition"
          ? `AND src.${quoteIdent(table.business_date_column)} = ${dateLiteral(row.business_date)}`
          : "";
      const order = table.key ? `ORDER BY src.${quoteIdent(table.key)}` : "";
      samples = await sampleRows(
        query,
        `
          SELECT CAST(to_json(src) AS VARCHAR) AS row_json
          FROM ${source} AS src
          ${join}
          WHERE parent.${parentColumn} IS NULL
          ${dateSql}
          ${order}
          LIMIT ${SAMPLE_LIMIT}
        `,
      );
    }
    output.push(
      result(table, check, row.business_date, {
        status,
        metric_name: "orphan_rows",
        metric_value: row.failed,
        threshold: 0,
        comparator: "==",
        failed_row_count: row.failed,
        total_row_count: row.total,
        samples,
        detail: {
          failed: row.failed,
          total: row.total,
          ref: `${check.references_table}.${check.references_column}`,
        },
      }),
    );
  }
  return output;
}

function parseTimestamp(value) {
  if (value == null || value === "") return null;
  const text = String(value).replace("T", " ").slice(0, 19);
  const [day, time] = text.split(" ");
  if (!day || !time) return null;
  const [year, month, date] = day.split("-").map(Number);
  const [hour, minute, second] = time.split(":").map(Number);
  const pad = (part) => String(part).padStart(2, "0");
  return {
    minuteText: `${day} ${pad(hour)}:${pad(minute)}`,
    ms: Date.UTC(year, month - 1, date, hour, minute, second || 0),
  };
}

function deadlineOf(businessDate, hours) {
  const [year, month, date] = businessDate.split("-").map(Number);
  const ms = Date.UTC(year, month - 1, date, 0, 0, 0) + hours * 3600000;
  const stamp = new Date(ms);
  const pad = (part) => String(part).padStart(2, "0");
  return {
    ms,
    minuteText: `${stamp.getUTCFullYear()}-${pad(stamp.getUTCMonth() + 1)}-${pad(stamp.getUTCDate())} ${pad(stamp.getUTCHours())}:${pad(stamp.getUTCMinutes())}`,
  };
}

async function freshness(query, suite, table, check) {
  if (check.deadline_hours == null || !check.timestamp_column) {
    throw new Error(`${check.id} requires timestamp_column and deadline_hours`);
  }
  const timestamp = quoteIdent(check.timestamp_column);
  const source = quoteIdent(table.name);
  let measured;
  if (check.scope === "table") {
    const row = (
      await query(`SELECT count(*)::DOUBLE AS total, CAST(max(${timestamp}) AS VARCHAR) AS max_loaded FROM ${source}`)
    )[0];
    measured = [{ business_date: suite.as_of, total: Math.round(num(row.total)), max_loaded: row.max_loaded }];
  } else {
    const dateCol = quoteIdent(table.business_date_column);
    const rows = await query(`
      SELECT CAST(${dateCol} AS VARCHAR) AS business_date,
             count(*)::DOUBLE AS total,
             CAST(max(${timestamp}) AS VARCHAR) AS max_loaded
      FROM ${source}
      GROUP BY ${dateCol}
      ORDER BY ${dateCol}
    `);
    measured = rows.map((row) => ({
      business_date: asDate(row.business_date),
      total: Math.round(num(row.total)),
      max_loaded: row.max_loaded,
    }));
  }
  const output = [];
  for (const row of measured) {
    const deadline = deadlineOf(row.business_date, Number(check.deadline_hours));
    const loaded = parseTimestamp(row.max_loaded);
    let lateness = null;
    let status = "fail";
    if (loaded) {
      lateness = (loaded.ms - deadline.ms) / 3600000;
      status = lateness > 1e-9 ? "fail" : "pass";
    }
    let samples = [];
    if (status === "fail") {
      const dateSql =
        check.scope === "partition"
          ? `${quoteIdent(table.business_date_column)} = ${dateLiteral(row.business_date)}`
          : "1 = 1";
      const order = table.key ? quoteIdent(table.key) : "";
      samples = await sampleRows(query, sampleSelect(source, dateSql, order));
    }
    output.push(
      result(table, check, row.business_date, {
        status,
        metric_name: "lateness_hours",
        metric_value: lateness,
        threshold: 0,
        comparator: "<=",
        failed_row_count: status === "fail" ? row.total : 0,
        total_row_count: row.total,
        samples,
        detail: {
          lateness,
          loaded: loaded ? loaded.minuteText : null,
          deadline: deadline.minuteText,
          timestamp: check.timestamp_column,
          total: row.total,
        },
      }),
    );
  }
  return output;
}

async function volume(query, table, check) {
  if (check.scope !== "partition") throw new Error(`${check.id} volume checks must be partition scoped`);
  if (check.max_deviation_pct == null) throw new Error(`${check.id} requires max_deviation_pct`);
  const window = check.window_days || 14;
  const dateCol = quoteIdent(table.business_date_column);
  const rows = await query(`
    SELECT CAST(${dateCol} AS VARCHAR) AS business_date, count(*)::DOUBLE AS n
    FROM ${quoteIdent(table.name)}
    GROUP BY ${dateCol}
    ORDER BY ${dateCol}
  `);
  const series = rows.map((row) => ({ date: asDate(row.business_date), count: Math.round(num(row.n)) }));
  const output = [];
  for (let index = 0; index < series.length; index += 1) {
    const current = series[index];
    const history = series.slice(Math.max(0, index - window), index).map((item) => item.count);
    if (history.length < window) {
      output.push(
        result(table, check, current.date, {
          status: "skipped",
          metric_name: "volume_deviation",
          metric_value: null,
          threshold: Number(check.max_deviation_pct),
          comparator: "<=",
          failed_row_count: 0,
          total_row_count: current.count,
          detail: { have: history.length, window, count: current.count },
        }),
      );
      continue;
    }
    const { deviation, center } = deviationFromMedian(current.count, history);
    const finite = Number.isFinite(deviation);
    const status = !finite || deviation > Number(check.max_deviation_pct) + 1e-12 ? "fail" : "pass";
    const gap = Math.abs(current.count - Math.round(center));
    let samples = [];
    if (status === "fail") {
      const order = table.key ? quoteIdent(table.key) : "";
      samples = await sampleRows(
        query,
        sampleSelect(
          quoteIdent(table.name),
          `${quoteIdent(table.business_date_column)} = ${dateLiteral(current.date)}`,
          order,
        ),
      );
    }
    output.push(
      result(table, check, current.date, {
        status,
        metric_name: "volume_deviation",
        metric_value: finite ? deviation : null,
        threshold: Number(check.max_deviation_pct),
        comparator: "<=",
        failed_row_count: status === "fail" ? gap : 0,
        total_row_count: current.count,
        samples,
        detail: {
          count: current.count,
          deviation: finite ? deviation : null,
          center,
          window,
          limit: Number(check.max_deviation_pct),
          finite,
          gap,
        },
      }),
    );
  }
  return output;
}

async function categoricalDrift(query, table, check, window) {
  const dateCol = quoteIdent(table.business_date_column);
  const column = quoteIdent(check.column);
  const rows = await query(`
    SELECT CAST(${dateCol} AS VARCHAR) AS business_date,
           CAST(${column} AS VARCHAR) AS category,
           count(*)::DOUBLE AS n
    FROM ${quoteIdent(table.name)}
    GROUP BY ${dateCol}, ${column}
    ORDER BY ${dateCol}
  `);
  const counts = new Map();
  for (const row of rows) {
    const date = asDate(row.business_date);
    if (!counts.has(date)) counts.set(date, new Map());
    const category = row.category == null ? "None" : String(row.category);
    counts.get(date).set(category, Math.round(num(row.n)));
  }
  const dates = [...counts.keys()].sort();
  return psiResults(table, check, window, dates, counts);
}

function psiResults(table, check, window, dates, counts) {
  const output = [];
  for (let index = 0; index < dates.length; index += 1) {
    const businessDate = dates[index];
    const day = counts.get(businessDate);
    const total = [...day.values()].reduce((sum, count) => sum + count, 0);
    if (index < window) {
      output.push(skipDrift(table, check, businessDate, total, window, index));
      continue;
    }
    const categories = new Set();
    for (const prior of dates.slice(0, window)) {
      for (const category of counts.get(prior).keys()) categories.add(category);
    }
    for (const category of day.keys()) categories.add(category);
    const ordered = [...categories].sort();
    const expected = ordered.map((category) =>
      dates.slice(0, window).reduce((sum, prior) => sum + (counts.get(prior).get(category) || 0), 0),
    );
    const actual = ordered.map((category) => day.get(category) || 0);
    const value = psi(expected, actual);
    const status = value > Number(check.threshold) + 1e-12 ? "fail" : "pass";
    let samples = [];
    if (status === "fail") {
      const expectedTotal = expected.reduce((sum, count) => sum + count, 0) || 1;
      const actualTotal = actual.reduce((sum, count) => sum + count, 0) || 1;
      samples = ordered.map((category, categoryIndex) => ({
        category,
        actual_rows: actual[categoryIndex],
        actual_share: actual[categoryIndex] / actualTotal,
        reference_rows: expected[categoryIndex],
        reference_share: expected[categoryIndex] / expectedTotal,
      }));
    }
    output.push(
      result(table, check, businessDate, {
        status,
        metric_name: "psi",
        metric_value: value,
        threshold: Number(check.threshold),
        comparator: "<=",
        failed_row_count: status === "fail" ? total : 0,
        total_row_count: total,
        samples,
        detail: { psi: value, threshold: Number(check.threshold), column: check.column, window },
      }),
    );
  }
  return output;
}

function skipDrift(table, check, businessDate, total, window, index) {
  return result(table, check, businessDate, {
    status: "skipped",
    metric_name: "psi",
    metric_value: null,
    threshold: Number(check.threshold),
    comparator: "<=",
    failed_row_count: 0,
    total_row_count: total,
    detail: { window, index: index + 1, column: check.column },
  });
}

async function numericDrift(query, table, check, window) {
  const dateCol = quoteIdent(table.business_date_column);
  const column = quoteIdent(check.column);
  const rows = await query(`
    SELECT CAST(${dateCol} AS VARCHAR) AS business_date,
           CAST(${column} AS DOUBLE) AS value,
           count(*)::DOUBLE AS n
    FROM ${quoteIdent(table.name)}
    GROUP BY 1, 2
  `);
  const groupedValues = new Map();
  for (const row of rows) {
    const date = asDate(row.business_date);
    if (!groupedValues.has(date)) groupedValues.set(date, []);
    groupedValues.get(date).push([num(row.value), Math.round(num(row.n))]);
  }
  const dates = [...groupedValues.keys()].sort();
  const bins = check.bins || 5;
  const output = [];
  for (let index = 0; index < dates.length; index += 1) {
    const businessDate = dates[index];
    const total = groupedValues.get(businessDate).reduce((sum, pair) => sum + pair[1], 0);
    if (index < window) {
      output.push(skipDrift(table, check, businessDate, total, window, index));
      continue;
    }
    const referencePairs = [];
    for (const prior of dates.slice(0, window)) referencePairs.push(...groupedValues.get(prior));
    const referenceValues = expandPairs(referencePairs);
    const edges = binEdges(referenceValues, bins);
    const expected = histogram(referenceValues, edges);
    const actual = histogram(expandPairs(groupedValues.get(businessDate)), edges);
    const value = psi(expected, actual);
    const status = value > Number(check.threshold) + 1e-12 ? "fail" : "pass";
    const samples = status === "fail" ? binSamples(edges, expected, actual) : [];
    output.push(
      result(table, check, businessDate, {
        status,
        metric_name: "psi",
        metric_value: value,
        threshold: Number(check.threshold),
        comparator: "<=",
        failed_row_count: status === "fail" ? total : 0,
        total_row_count: total,
        samples,
        detail: { psi: value, threshold: Number(check.threshold), column: check.column, window },
      }),
    );
  }
  return output;
}

function binSamples(edges, expected, actual) {
  const expectedTotal = expected.reduce((sum, count) => sum + count, 0) || 1;
  const actualTotal = actual.reduce((sum, count) => sum + count, 0) || 1;
  return expected.map((expectedCount, index) => ({
    bin: index + 1,
    left: edges[index] === Number.NEGATIVE_INFINITY ? null : edges[index],
    right: edges[index + 1] === Number.POSITIVE_INFINITY ? null : edges[index + 1],
    actual_rows: actual[index],
    actual_share: actual[index] / actualTotal,
    reference_rows: expectedCount,
    reference_share: expectedCount / expectedTotal,
  }));
}

function formatGolden(name, value) {
  if (value == null || value === "") return null;
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (name.includes("weight")) return number.toFixed(2);
  if (Math.abs(number - Math.round(number)) < 1e-6) return String(Math.round(number));
  return number.toFixed(2);
}

function goldenDiff(actual, expected) {
  return Math.abs(Math.round(Number(actual) * 100) - Math.round(Number(expected) * 100)) / 100;
}

async function golden(query, table, check, goldenByDate) {
  if (check.scope !== "partition") throw new Error(`${check.id} golden reconciliation must be partition scoped`);
  if (!check.metrics?.length) throw new Error(`${check.id} requires metrics`);
  const dateCol = quoteIdent(table.business_date_column);
  const selectList = check.metrics
    .map((metric) => {
      const expression = String(metric.expression).replaceAll(" ", "");
      if (!METRIC.test(expression)) throw new Error(`Unsafe metric expression: ${metric.expression}`);
      return `CAST(${expression} AS DOUBLE) AS ${quoteIdent(metric.name)}`;
    })
    .join(", ");
  const rows = await query(`
    SELECT CAST(${dateCol} AS VARCHAR) AS business_date, ${selectList}
    FROM ${quoteIdent(table.name)}
    GROUP BY ${dateCol}
    ORDER BY ${dateCol}
  `);
  const actual = new Map();
  for (const row of rows) actual.set(asDate(row.business_date), row);
  const dates = [...new Set([...actual.keys(), ...Object.keys(goldenByDate)])].sort();
  const output = [];
  for (const businessDate of dates) {
    const breaches = [];
    const evidence = [];
    for (const metric of check.metrics) {
      const actualValue = actual.has(businessDate) ? actual.get(businessDate)[metric.name] : null;
      const expectedValue = goldenByDate[businessDate]?.[metric.name] ?? null;
      let breach = null;
      if (actualValue == null || expectedValue == null || expectedValue === "") {
        breach = {
          name: metric.name,
          actual: actualValue,
          expected: expectedValue,
          missing: true,
        };
      } else if (metric.tolerance_abs != null) {
        const difference = goldenDiff(actualValue, expectedValue);
        if (difference > Number(metric.tolerance_abs) + 1e-9) {
          breach = {
            name: metric.name,
            actual: actualValue,
            expected: expectedValue,
            difference,
            tolerance: Number(metric.tolerance_abs),
            kind: "abs",
          };
        }
      } else if (metric.tolerance_pct != null) {
        const difference = goldenDiff(actualValue, expectedValue);
        const base = Math.abs(Number(expectedValue));
        const ratio = base === 0 ? (Number(actualValue) === 0 ? 0 : 1) : difference / base;
        if (ratio > Number(metric.tolerance_pct) + 1e-12) {
          breach = {
            name: metric.name,
            actual: actualValue,
            expected: expectedValue,
            difference: ratio,
            tolerance: Number(metric.tolerance_pct),
            kind: "pct",
          };
        }
      } else if (goldenDiff(actualValue, expectedValue) !== 0) {
        breach = {
          name: metric.name,
          actual: actualValue,
          expected: expectedValue,
          difference: goldenDiff(actualValue, expectedValue),
          tolerance: 0,
          kind: "abs",
        };
      }
      evidence.push({
        metric: metric.name,
        actual: formatGolden(metric.name, actualValue),
        expected: formatGolden(metric.name, expectedValue),
        breached: breach != null,
      });
      if (breach) breaches.push(breach);
    }
    output.push(
      result(table, check, businessDate, {
        status: breaches.length ? "fail" : "pass",
        metric_name: "metrics_breached",
        metric_value: breaches.length,
        threshold: 0,
        comparator: "==",
        failed_row_count: breaches.length,
        total_row_count: check.metrics.length,
        samples: breaches.length ? evidence : [],
        detail: { breaches, metrics: check.metrics.length },
      }),
    );
  }
  return output;
}

async function drift(query, table, check) {
  if (check.scope !== "partition") throw new Error(`${check.id} drift checks must be partition scoped`);
  if (check.threshold == null) throw new Error(`${check.id} requires threshold`);
  const window = check.window_days || 14;
  if (check.numeric) return numericDrift(query, table, check, window);
  return categoricalDrift(query, table, check, window);
}

const RUNNERS = {
  completeness,
  uniqueness,
  validity,
  accepted_values: acceptedValues,
  referential_integrity: referential,
  freshness,
  volume_anomaly: volume,
  distribution_drift: drift,
  golden_reconciliation: golden,
};

export async function runSuite(query, suite, goldenByDate, options = {}) {
  const plan = [];
  for (const table of suite.tables) {
    for (const check of table.checks) plan.push({ table, check });
  }
  const results = [];
  for (let index = 0; index < plan.length; index += 1) {
    const { table, check } = plan[index];
    options.onProgress?.({ index, total: plan.length, checkId: check.id });
    const runner = RUNNERS[check.type];
    if (!runner) throw new Error(`Unsupported check type ${check.type}`);
    const rows =
      check.type === "volume_anomaly" || check.type === "distribution_drift"
        ? await runner(query, table, check)
        : check.type === "golden_reconciliation"
          ? await runner(query, table, check, goldenByDate)
          : await runner(query, suite, table, check);
    results.push(...rows);
  }
  options.onProgress?.({ index: plan.length, total: plan.length, checkId: null });
  return { results, scores: scoreRun(results, suite) };
}

function weightFor(severity, weights) {
  if (!(severity in weights)) throw new Error(`Unknown severity ${severity}`);
  return Number(weights[severity]);
}

function scoreGroup(rows, businessDate, tableName, suite) {
  const skipped = rows.filter((row) => row.status === "skipped");
  const considered = rows.filter((row) => row.status === "pass" || row.status === "fail" || row.status === "error");
  const weightTotal = considered.reduce((sum, row) => sum + weightFor(row.severity, suite.severity_weights), 0);
  const weightPassed = considered
    .filter((row) => row.status === "pass")
    .reduce((sum, row) => sum + weightFor(row.severity, suite.severity_weights), 0);
  const failed = considered.filter((row) => row.status !== "pass");
  const criticalFailed = failed.filter((row) => row.severity === "critical").length;
  const score = weightTotal === 0 ? 100 : round4((100 * weightPassed) / weightTotal);
  let status = "pass";
  if (score + 1e-9 < Number(suite.pass_score) || (suite.fail_on_critical && criticalFailed > 0)) {
    status = "fail";
  }
  return {
    business_date: businessDate,
    table_name: tableName,
    score,
    status,
    checks_total: considered.length,
    checks_failed: failed.length,
    checks_skipped: skipped.length,
    critical_failed: criticalFailed,
    weight_passed: weightPassed,
    weight_total: weightTotal,
  };
}

export function scoreRun(results, suite) {
  const grouped = new Map();
  const byDay = new Map();
  for (const row of results) {
    const key = `${row.business_date}\t${row.table_name}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(row);
    if (!byDay.has(row.business_date)) byDay.set(row.business_date, []);
    byDay.get(row.business_date).push(row);
  }
  const scores = [];
  const keys = [...grouped.keys()].sort((left, right) => {
    const [leftDate, leftTable] = left.split("\t");
    const [rightDate, rightTable] = right.split("\t");
    return leftDate < rightDate ? -1 : leftDate > rightDate ? 1 : leftTable < rightTable ? -1 : leftTable > rightTable ? 1 : 0;
  });
  for (const key of keys) {
    const [businessDate, tableName] = key.split("\t");
    scores.push(scoreGroup(grouped.get(key), businessDate, tableName, suite));
  }
  for (const businessDate of [...byDay.keys()].sort()) {
    scores.push(scoreGroup(byDay.get(businessDate), businessDate, DAY_TABLE, suite));
  }
  return scores;
}

function ratio(numerator, denominator) {
  if (denominator === 0) return 1;
  return numerator / denominator;
}

export function evaluateResults(results, defects) {
  const byKey = new Map();
  for (const row of results) byKey.set(`${row.check_id}|${row.business_date}`, row);
  const failKeys = new Set();
  for (const [key, row] of byKey) {
    if (row.status === "fail") failKeys.add(key);
  }
  const missed = [];
  const caught = new Set();
  const defectKeys = new Set(defects.map((defect) => `${defect.check_id}|${defect.business_date}`));
  let rowApplicable = 0;
  let rowCaught = 0;
  for (const defect of defects) {
    const key = `${defect.check_id}|${defect.business_date}`;
    const found = byKey.get(key);
    const statusHit = found != null && found.status === "fail";
    let rowHit = true;
    if (defect.min_failed_rows != null) {
      rowApplicable += 1;
      const observed = found == null ? 0 : Number(found.failed_row_count || 0);
      rowHit = observed >= Number(defect.min_failed_rows);
      if (statusHit && rowHit) rowCaught += 1;
    }
    if (statusHit && rowHit) caught.add(key);
    else {
      missed.push({
        id: defect.id,
        check_id: defect.check_id,
        business_date: defect.business_date,
        status: found ? found.status : null,
        failed_row_count: found ? Number(found.failed_row_count || 0) : null,
        min_failed_rows: defect.min_failed_rows,
        description: defect.description,
      });
    }
  }
  const unexpected = [];
  for (const key of [...failKeys].sort()) {
    if (defectKeys.has(key)) continue;
    const found = byKey.get(key);
    unexpected.push({
      check_id: found.check_id,
      business_date: found.business_date,
      table: found.table_name,
      failed_row_count: Number(found.failed_row_count || 0),
    });
  }
  const truePositives = caught.size;
  const falsePositives = unexpected.length;
  const falseNegatives = missed.length;
  return {
    defects_total: defects.length,
    defects_caught: truePositives,
    fails_total: failKeys.size,
    true_positives: truePositives,
    false_positives: falsePositives,
    false_negatives: falseNegatives,
    precision: ratio(truePositives, truePositives + falsePositives),
    recall: ratio(truePositives, truePositives + falseNegatives),
    row_level_applicable: rowApplicable,
    row_level_caught: rowCaught,
    row_level_recall: ratio(rowCaught, rowApplicable),
    missed,
    unexpected,
  };
}

export function parseGolden(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(",");
  const parsed = {};
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const cells = line.split(",");
    const businessDate = cells[0].slice(0, 10);
    parsed[businessDate] = {};
    header.forEach((name, index) => {
      if (name !== "business_date" && cells[index] != null && cells[index] !== "") {
        parsed[businessDate][name] = cells[index];
      }
    });
  }
  return parsed;
}
