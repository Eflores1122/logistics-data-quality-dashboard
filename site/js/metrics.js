/** Volume and PSI helpers. Same definitions as src/rutanorte_dq/metrics.py. */

export function psi(expectedCounts, actualCounts, eps = 1e-4) {
  if (expectedCounts.length !== actualCounts.length || expectedCounts.length === 0) {
    throw new Error("PSI inputs must be non-empty and the same length");
  }
  const expected = shares(expectedCounts, eps);
  const actual = shares(actualCounts, eps);
  let total = 0;
  for (let index = 0; index < expected.length; index += 1) {
    total += (actual[index] - expected[index]) * Math.log(actual[index] / expected[index]);
  }
  return total;
}

function shares(counts, eps) {
  const adjusted = counts.map((count) => Math.max(Number(count), 0) + eps);
  const total = adjusted.reduce((sum, count) => sum + count, 0);
  return adjusted.map((count) => count / total);
}

export function median(values) {
  if (!values.length) throw new Error("history must not be empty");
  const sorted = values.map(Number).sort((left, right) => left - right);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

export function deviationFromMedian(current, history) {
  const center = median(history);
  if (center === 0) {
    return { deviation: Number(current) === 0 ? 0 : Infinity, center };
  }
  return { deviation: Math.abs(Number(current) / center - 1), center };
}

export function quantile(sortedValues, q) {
  if (!sortedValues.length) throw new Error("quantile of an empty series");
  if (q <= 0) return Number(sortedValues[0]);
  if (q >= 1) return Number(sortedValues[sortedValues.length - 1]);
  const position = q * (sortedValues.length - 1);
  const low = Math.floor(position);
  const high = Math.ceil(position);
  if (low === high) return Number(sortedValues[low]);
  const weight = position - low;
  return Number(sortedValues[low]) * (1 - weight) + Number(sortedValues[high]) * weight;
}

export function binEdges(values, bins) {
  if (bins < 1) throw new Error("bins must be positive");
  const ordered = values.map(Number).sort((left, right) => left - right);
  if (!ordered.length) return [Number.NEGATIVE_INFINITY, Number.POSITIVE_INFINITY];
  const internal = [];
  for (let step = 1; step < bins; step += 1) {
    const cut = quantile(ordered, step / bins);
    if (!internal.length || cut > internal[internal.length - 1]) internal.push(cut);
  }
  return [Number.NEGATIVE_INFINITY, ...internal, Number.POSITIVE_INFINITY];
}

export function histogram(values, edges) {
  if (edges.length < 2) throw new Error("edges must contain at least two cut points");
  const counts = Array(edges.length - 1).fill(0);
  const last = counts.length - 1;
  for (const value of values) {
    const number = Number(value);
    let placed = last;
    for (let index = 0; index < counts.length; index += 1) {
      if (number <= edges[index + 1]) {
        placed = index;
        break;
      }
    }
    counts[placed] += 1;
  }
  return counts;
}

export function expandPairs(pairs) {
  const values = [];
  for (const [value, count] of pairs) {
    const n = Math.round(Number(count));
    for (let index = 0; index < n; index += 1) values.push(Number(value));
  }
  return values;
}
