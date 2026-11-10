/** Allow a single read-only statement against the local synthetic warehouse. */

const FORBIDDEN =
  /\b(insert|update|delete|drop|create|attach|copy|install|export|pragma|alter|truncate|call|load|grant|revoke|detach|begin|commit|rollback)\b/i;

export function guardSelect(sql) {
  if (typeof sql !== "string") {
    throw new Error("empty");
  }
  let text = sql.trim();
  if (!text) throw new Error("empty");
  text = text.replace(/;+\s*$/g, "").trim();
  if (text.includes(";")) throw new Error("multi");
  const stripped = text
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/--[^\n]*/g, " ")
    .trim();
  if (!/^(select|with)\b/i.test(stripped)) throw new Error("not-select");
  if (FORBIDDEN.test(stripped)) throw new Error("forbidden");
  return text;
}
