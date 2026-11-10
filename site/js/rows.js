/** Convert a DuckDB-WASM Arrow table into plain rows. */

function normalize(value) {
  if (typeof value === "bigint") return Number(value);
  if (value instanceof Date) {
    const pad = (part) => String(part).padStart(2, "0");
    return `${value.getUTCFullYear()}-${pad(value.getUTCMonth() + 1)}-${pad(value.getUTCDate())} ${pad(value.getUTCHours())}:${pad(value.getUTCMinutes())}:${pad(value.getUTCSeconds())}`;
  }
  if (value && typeof value === "object" && typeof value.toString === "function") {
    const name = value.constructor?.name || "";
    if (name.includes("Decimal") || name === "Uint8Array") return value.toString();
  }
  return value;
}

export function rowsFrom(table) {
  if (!table || typeof table.toArray !== "function") {
    throw new Error("Query did not return an Arrow table");
  }
  return table.toArray().map((row) => {
    const source = typeof row.toJSON === "function" ? row.toJSON() : row;
    const out = {};
    for (const key of Object.keys(source)) out[key] = normalize(source[key]);
    return out;
  });
}
