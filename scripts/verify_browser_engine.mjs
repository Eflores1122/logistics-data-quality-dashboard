/**
 * Run the browser check engine on the exported parquet with DuckDB-WASM
 * and compare it to the Python reference output.
 */
import { createRequire } from "node:module";
import { Worker as NodeWorker } from "node:worker_threads";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

class DuckWorker {
  constructor(filename) {
    this.worker = new NodeWorker(filename);
    this.listeners = new Map();
    this.worker.on("message", (data) => {
      this.dispatch("message", { data });
    });
    this.worker.on("error", (error) => {
      this.dispatch("error", { error });
    });
  }

  dispatch(type, event) {
    const handler = this[`on${type}`];
    if (typeof handler === "function") handler(event);
    for (const listener of this.listeners.get(type) || []) listener(event);
  }

  addEventListener(type, listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(listener);
  }

  removeEventListener(type, listener) {
    const list = this.listeners.get(type) || [];
    const index = list.indexOf(listener);
    if (index >= 0) list.splice(index, 1);
  }

  postMessage(data, transfer) {
    this.worker.postMessage(data, transfer);
  }

  terminate() {
    return this.worker.terminate();
  }
}

import { evaluateResults, parseGolden, runSuite } from "../site/js/engine.js";
import { binEdges, histogram, psi } from "../site/js/metrics.js";
import { rowsFrom } from "../site/js/rows.js";
import { guardSelect } from "../site/js/sql_guard.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = path.join(root, "site", "data");
const require = createRequire(import.meta.url);
const duckdb = require("@duckdb/duckdb-wasm");

function assertClose(actual, expected, label) {
  if (expected == null) {
    if (actual != null) throw new Error(`${label}: expected null, got ${actual}`);
    return;
  }
  const diff = Math.abs(Number(actual) - Number(expected));
  const tolerance = 1e-4 * Math.max(1, Math.abs(Number(expected)));
  if (diff > tolerance) throw new Error(`${label}: ${actual} != ${expected} (diff ${diff})`);
}

function checkMetrics() {
  const value = psi([50, 50], [90, 10]);
  assertClose(value, 0.8788845176296498, "psi fixture");
  const edges = binEdges([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5);
  const counts = histogram([1, 2, 3, 10], edges);
  if (counts.join(",") !== "2,1,0,0,1") {
    throw new Error(`histogram fixture ${counts.join(",")}`);
  }
  if (guardSelect("SELECT 1").length < 8) throw new Error("guard stripped a valid select");
  let rejected = false;
  try {
    guardSelect("DROP TABLE shipments");
  } catch {
    rejected = true;
  }
  if (!rejected) throw new Error("guard accepted DROP");
}

async function openWarehouse() {
  const wasmPath = require.resolve("@duckdb/duckdb-wasm/dist/duckdb-eh.wasm");
  const workerPath = path.join(root, "scripts", "duckdb_worker.cjs");
  const worker = new DuckWorker(workerPath);
  const db = new duckdb.AsyncDuckDB({ log() {} }, worker);
  await db.instantiate(wasmPath);
  const tables = ["hubs", "customers", "tracking_scans", "shipments", "daily_route_kpis"];
  for (const table of tables) {
    const bytes = fs.readFileSync(path.join(dataDir, `${table}.parquet`));
    await db.registerFileBuffer(`${table}.parquet`, new Uint8Array(bytes));
  }
  const conn = await db.connect();
  for (const table of tables) {
    await conn.query(
      `CREATE TABLE ${table} AS SELECT * FROM read_parquet('${table}.parquet')`,
    );
  }
  return {
    db,
    conn,
    worker,
    async query(sql) {
      const table = await conn.query(sql);
      return rowsFrom(table);
    },
  };
}

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(dataDir, name), "utf8"));
}

async function main() {
  checkMetrics();
  const suite = readJson("suite.json");
  const defects = readJson("defects.json").defects;
  const reference = readJson("reference_results.json");
  const golden = parseGolden(fs.readFileSync(path.join(dataDir, "golden.csv"), "utf8"));
  const warehouse = await openWarehouse();
  try {
    const probe = await warehouse.query(
      "SELECT count(*)::DOUBLE AS n FROM shipments",
    );
    if (Math.round(probe[0].n) !== 44220) {
      throw new Error(`shipment probe returned ${JSON.stringify(probe)}`);
    }
    const started = Date.now();
    const { results, scores } = await runSuite(warehouse.query, suite, golden, {
      onProgress({ index, total, checkId }) {
        if (index === total || index % 10 === 0) {
          process.stdout.write(`\rchecks ${index}/${total} ${checkId || ""}`.padEnd(72));
        }
      },
    });
    process.stdout.write("\n");
    console.log(`engine finished in ${((Date.now() - started) / 1000).toFixed(1)}s`);
    if (results.length !== reference.results.length) {
      throw new Error(`result count ${results.length} != ${reference.results.length}`);
    }
    const actual = new Map(results.map((row) => [`${row.business_date}|${row.check_id}`, row]));
    const mismatches = [];
    for (const expected of reference.results) {
      const key = `${expected.business_date}|${expected.check_id}`;
      const row = actual.get(key);
      if (!row) {
        mismatches.push(`${key} missing`);
        continue;
      }
      if (row.status !== expected.status) {
        mismatches.push(`${key} status ${row.status} != ${expected.status}`);
      }
      if (row.failed_row_count !== expected.failed_row_count) {
        mismatches.push(
          `${key} failed rows ${row.failed_row_count} != ${expected.failed_row_count}`,
        );
      }
      if (row.total_row_count !== expected.total_row_count) {
        mismatches.push(`${key} total ${row.total_row_count} != ${expected.total_row_count}`);
      }
      try {
        assertClose(row.metric_value, expected.metric_value, key);
      } catch (error) {
        mismatches.push(error.message);
      }
    }
    if (mismatches.length) {
      console.error(mismatches.slice(0, 30).join("\n"));
      throw new Error(`${mismatches.length} mismatches`);
    }
    const dayScores = scores.filter((row) => row.table_name === "__day__");
    for (const expected of reference.days) {
      const row = dayScores.find((item) => item.business_date === expected.business_date);
      if (!row) throw new Error(`missing day ${expected.business_date}`);
      if (row.status !== expected.status) {
        throw new Error(`${expected.business_date} sla ${row.status} != ${expected.status}`);
      }
      assertClose(row.score, expected.score, `${expected.business_date} score`);
      if (row.checks_failed !== expected.checks_failed) {
        throw new Error(`${expected.business_date} failed checks ${row.checks_failed}`);
      }
    }
    const evaluation = evaluateResults(results, defects);
    if (evaluation.defects_caught !== 20 || evaluation.false_positives !== 0) {
      throw new Error(`evaluation ${JSON.stringify(evaluation)}`);
    }
    if (evaluation.precision !== 1 || evaluation.recall !== 1 || evaluation.row_level_recall !== 1) {
      throw new Error("precision or recall drifted");
    }
    const emails = results.find(
      (row) => row.check_id === "customers_email_completeness" && row.business_date === "2026-10-10",
    );
    if (!emails || emails.samples.length !== 15 || emails.samples.some((row) => row.email != null)) {
      throw new Error(`email samples ${emails ? emails.samples.length : "missing"}`);
    }
    const channel = results.find(
      (row) => row.check_id === "shipments_channel_drift" && row.business_date === "2026-10-13",
    );
    const counter = channel?.samples.find((row) => row.category === "counter");
    if (!counter || counter.actual_rows !== 800) {
      throw new Error(`channel sample ${JSON.stringify(counter)}`);
    }
    const late = await warehouse.query(`
      SELECT CAST(max(loaded_at) AS VARCHAR) AS loaded
      FROM tracking_scans
      WHERE business_date = DATE '2026-10-15'
    `);
    if (!String(late[0].loaded).includes("2026-10-16 20:00")) {
      throw new Error(`freshness stamp ${late[0].loaded}`);
    }
    console.log("browser engine matches the Python reference");
  } finally {
    await warehouse.conn.close();
    await warehouse.db.terminate();
    await warehouse.worker.terminate();
  }
}

process.on("unhandledRejection", (error) => {
  console.error("unhandled", error);
  process.exit(1);
});
main().catch((error) => {
  console.error(error);
  process.exit(1);
});
