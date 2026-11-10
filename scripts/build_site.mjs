import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import * as esbuild from "esbuild";

const require = createRequire(import.meta.url);
const wasm = require.resolve("@duckdb/duckdb-wasm/dist/duckdb-eh.wasm");
const worker = require.resolve("@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js");
const browser = require.resolve("@duckdb/duckdb-wasm/dist/duckdb-browser.mjs");
const vendor = path.resolve("site/vendor");
const assets = path.resolve("site/assets");

await mkdir(vendor, { recursive: true });
await mkdir(assets, { recursive: true });
await copyFile(wasm, path.join(vendor, "duckdb-eh.wasm"));
await copyFile(worker, path.join(vendor, "duckdb-browser-eh.worker.js"));

await esbuild.build({
  entryPoints: ["site/js/app.js"],
  bundle: true,
  format: "esm",
  outfile: "site/assets/app.js",
  platform: "browser",
  target: ["es2022"],
  alias: {
    "@duckdb/duckdb-wasm": browser,
  },
  legalComments: "none",
});

console.log("Built site/assets/app.js and site/vendor/");
