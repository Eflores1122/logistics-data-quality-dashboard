/**
 * worker_threads entry that exposes the browser-style hooks DuckDB-WASM expects.
 * The published node worker sets globalThis.onmessage and calls globalThis.postMessage.
 */
const { parentPort } = require("node:worker_threads");

globalThis.postMessage = (data, transfer) => {
  parentPort.postMessage(data, transfer);
};

parentPort.on("message", (data) => {
  if (typeof globalThis.onmessage === "function") {
    globalThis.onmessage({ data });
  }
});

require("@duckdb/duckdb-wasm/dist/duckdb-node-eh.worker.cjs");
