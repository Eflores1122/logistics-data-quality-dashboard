/** Interface copy. Numbers are filled from the check run, not from this file. */

const STRINGS = {
  es: {
    docTitle: "RutaNorte calidad de datos",
    skip: "Saltar a la tendencia",
    mark: "RutaNorte",
    markSub: "calidad de datos",
    langLabel: "Idioma",
    repo: "Repositorio",
    profile: "GitHub",
    title: "Sala de control",
    loading: "Cargando DuckDB y el almacén sintético de semilla 42.",
    progressWasm: "Preparando DuckDB en este navegador.",
    progressData: "Leyendo hubs, clientes, escaneos, envíos y el mart.",
    progressCheck: "Corriendo {check} ({done} de {total}).",
    errorTitle: "Los checks no terminaron",
    counts:
      "Este navegador contó {shipments} envíos, {customers} clientes, {scans} escaneos y {hubs} sucursales en {days} días.",
    detection:
      "{failingChecks} checks fallan. {failingDays} de {days} días no pasan el SLA. Precisión {precision}, recall {recall}, recall por filas {rowCaught} de {rowApplicable}.",
    selected: "{date}: puntaje {score}, SLA {sla}, {failedText}.",
    oneFail: "1 check en falla",
    manyFail: "{failed} checks en falla",
    lowest: "El puntaje más bajo es {score} el {date}.",
    passWithFail: "{date} pasa el SLA con {score} y {failed} check en falla.",
    aboveLine: "{date} queda en {score}, por encima de {line}, y el SLA falla por un check crítico.",
    late: "{table} llegó {hours} horas después del límite ({loaded}, límite {deadline}).",
    source:
      "Fuente: SQL de site/js/engine.js sobre los parquet de site/data. Suite checks/rutanorte_daily.yaml. Catálogo data/ground_truth/injected_defects.yaml. Semilla 42. {seconds} s en este navegador.",
    mismatch: "El conteo leído no coincide con manifest.json en {tables}.",
    trendTitle: "Puntaje diario",
    trendHint:
      "Clic o toque un día para filtrarlo. El cuadro falla el SLA. El rombo pasa el SLA con algún check en falla. El círculo pasa limpio. La línea horizontal es 95.",
    filterDate: "Fecha",
    filterTable: "Tabla",
    filterSeverity: "Severidad",
    filterStatus: "Estado",
    allDates: "Todas las fechas",
    allTables: "Todas las tablas",
    allSeverities: "Todas",
    allStatuses: "Todos",
    filterNote:
      "Fecha y tabla recorren checks, incidentes y linaje. Severidad y estado solo filtran la tabla de checks.",
    tabChecks: "Checks",
    tabIncidents: "Incidentes",
    tabLineage: "Linaje",
    tabSql: "Consulta",
    checksCaption: "{shown} checks visibles de {total} en la corrida.",
    emptyChecks: "Ningún check con estos filtros.",
    colDate: "Fecha",
    colCheck: "Check",
    colTable: "Tabla",
    colSeverity: "Severidad",
    colStatus: "Estado",
    colMetric: "Métrica",
    colRows: "Conteo",
    samples: "Filas de muestra (máximo 15)",
    noSamples: "Este resultado no guardó filas de muestra.",
    incidentsCaption:
      "{caught} de {total} defectos del catálogo quedaron detectados con el mínimo de filas pedido.",
    emptyIncidents: "Ningún incidente con estos filtros.",
    colDefect: "Defecto",
    colObserved: "Filas observadas",
    colMinimum: "Mínimo",
    colResult: "Resultado",
    caught: "detectado",
    missed: "no detectado",
    lineageIntro:
      "Las flechas salen de checks/rutanorte_daily.yaml. Los nodos crudos están declarados y el generador no los materializa. El color del texto marca la corrida de esta pantalla.",
    declared: "declarado",
    failDays: "falla en {count} días",
    cleanDays: "sin fallas",
    mermaidSummary: "Texto Mermaid del mismo grafo",
    rulesTitle: "Cómo se calcula el día",
    rulesScore:
      "Puntaje = 100 × peso de los checks que pasan / peso de los checks puntuados. Un check omitido, mientras se llena la mediana o la ventana de calibración, no entra al denominador.",
    rulesSla:
      "El día pasa si el puntaje es al menos {line} y ningún check crítico falló. La misma regla se aplica por tabla. Pesos: crítico 5, alto 3, medio 2, bajo 1.",
    rulesDrift:
      "El volumen usa la mediana de los 14 días previos. El PSI usa las primeras 14 fechas como base fija, para que un incidente no se meta en la referencia.",
    rulesId:
      "RFC, CURP, correo y teléfono se validan por forma, incluida una fecha de calendario real dentro de RFC y CURP. No son dígitos del SAT ni de RENAPO y no salen de este navegador.",
    rulesData:
      "RutaNorte Paquetería es ficticia. Personas, sucursales, guías y escaneos son sintéticos, semilla 42, del 1 sep 2026 al 15 oct 2026.",
    sqlIntro: "La consulta corre en el mismo DuckDB que acaba de puntuar los checks. Solo lectura.",
    sqlRun: "Ejecutar esta consulta",
    sqlRows: "{shown} filas.",
    sqlTruncated: "Se muestran las primeras {shown} filas.",
    sqlEmpty: "La consulta no devolvió filas.",
    presetChannel: "Ver la mezcla de canal del 13 oct",
    presetEmail: "Ver los correos nulos del 10 oct",
    presetLate: "Ver la carga de escaneos del 15 oct",
    errEmpty: "Escribe una consulta.",
    errMulti: "Una sola sentencia.",
    errSelect: "Solo SELECT o WITH.",
    errForbidden: "Esta consulta no está permitida. El almacén es de solo lectura.",
    errSql: "DuckDB rechazó la consulta: {message}",
    pass: "pasa",
    fail: "falla",
    skipped: "omitido",
    critical: "crítica",
    high: "alta",
    medium: "media",
    low: "baja",
    nullMetric: "{rate} nulos",
    invalidMetric: "{rate} inválidos",
    dupMetric: "{count} duplicadas",
    rejectMetric: "{count} fuera de lista",
    orphanMetric: "{count} huérfanas",
    lateMetric: "{hours} h",
    onTimeMetric: "a tiempo",
    volumeMetric: "{rate} vs mediana",
    psiMetric: "PSI {value}",
    goldenMetric: "{count} métricas",
    rowsPair: "{failed} / {total}",
    skipVolume: "Omitido. Hacen falta {window} días previos y hay {have}.",
    skipDrift: "Omitido. Las primeras {window} fechas calibran el PSI y esta es la número {day}.",
    completenessFail:
      "Tasa de nulos {rate} ({failed} de {total} filas), por encima de {threshold}.",
    completenessPass: "Tasa de nulos {rate} ({failed} de {total} filas), dentro de {threshold}.",
    validityFail:
      "{failed} de {present} valores no vacíos fallan {format}. Tasa {rate}, máximo {threshold}.",
    validityPass: "Tasa inválida de {format}: {rate}, dentro de {threshold}.",
    uniqueFail: "{failed} filas están en grupos duplicados de {columns}.",
    uniquePass: "{columns} es único en {total} filas.",
    acceptedFail: "{failed} de {total} filas quedan fuera de ({allowed}).",
    acceptedPass: "Las {total} filas están dentro de ({allowed}).",
    refFail: "{failed} de {total} filas apuntan a un {ref} que no existe.",
    refPass: "Cada fila apunta a {ref}.",
    freshFail: "Llegó {hours} horas después del límite (loaded_at {loaded}, límite {deadline}).",
    freshPass: "Llegó {hours} horas antes del límite (loaded_at {loaded}, límite {deadline}).",
    freshMissing: "No hay valor de {timestamp} para esta fecha.",
    volumeFail:
      "El conteo {count} se desvía {deviation} de la mediana de {window} días ({center}). El límite es {limit}.",
    volumePass:
      "El conteo {count} se desvía {deviation} de la mediana de {window} días ({center}), dentro de {limit}.",
    driftFail: "PSI {psi} supera {threshold} en {column}, contra las primeras {window} fechas.",
    driftPass: "PSI {psi} queda dentro de {threshold} en {column}, contra las primeras {window} fechas.",
    goldenPass: "Las {count} métricas golden coinciden.",
    goldenMissing: "{name} no está (real {actual}, esperado {expected}).",
    goldenAbs:
      "{name} real {actual}, esperado {expected} (diferencia absoluta {diff}, tolerancia {tolerance}).",
    colophon:
      "IBM Plex Sans, de IBM para interfaces técnicas densas. Las cifras tabulares alinean puntajes y conteos. IBM Plex Mono solo en identificadores, SQL y muestras. Acento #0C5C58, tinta de un sello de ruta, un solo color. #7A2424 se reserva para la palabra falla.",
    local: "La sala local con Streamlit sigue en dashboard/app.py.",
    synthetic: "Datos sintéticos. RutaNorte no es una empresa real.",
  },
  en: {
    docTitle: "RutaNorte data quality",
    skip: "Skip to the trend",
    mark: "RutaNorte",
    markSub: "data quality",
    langLabel: "Language",
    repo: "Repository",
    profile: "GitHub",
    title: "Control room",
    loading: "Loading DuckDB and the seed 42 synthetic warehouse.",
    progressWasm: "Preparing DuckDB in this browser.",
    progressData: "Reading hubs, customers, scans, shipments, and the mart.",
    progressCheck: "Running {check} ({done} of {total}).",
    errorTitle: "The checks did not finish",
    counts:
      "This browser counted {shipments} shipments, {customers} customers, {scans} scans, and {hubs} hubs across {days} days.",
    detection:
      "{failingChecks} checks fail. {failingDays} of {days} days miss the SLA. Precision {precision}, recall {recall}, row level recall {rowCaught} of {rowApplicable}.",
    selected: "{date}: score {score}, SLA {sla}, {failedText}.",
    oneFail: "1 failing check",
    manyFail: "{failed} failing checks",
    lowest: "The lowest score is {score} on {date}.",
    passWithFail: "{date} passes the SLA at {score} with {failed} failing check.",
    aboveLine: "{date} scores {score}, above {line}, and the SLA fails on a critical check.",
    late: "{table} arrived {hours} hours after the deadline ({loaded}, deadline {deadline}).",
    source:
      "Source: SQL in site/js/engine.js over the parquet files in site/data. Suite checks/rutanorte_daily.yaml. Catalog data/ground_truth/injected_defects.yaml. Seed 42. {seconds} s in this browser.",
    mismatch: "A count read here does not match manifest.json for {tables}.",
    trendTitle: "Daily score",
    trendHint:
      "Click or tap a day to filter. A square misses the SLA. A diamond passes the SLA with a failing check. A circle is clean. The horizontal line is 95.",
    filterDate: "Date",
    filterTable: "Table",
    filterSeverity: "Severity",
    filterStatus: "Status",
    allDates: "All dates",
    allTables: "All tables",
    allSeverities: "All",
    allStatuses: "All",
    filterNote: "Date and table apply to checks, incidents, and lineage. Severity and status filter the check table only.",
    tabChecks: "Checks",
    tabIncidents: "Incidents",
    tabLineage: "Lineage",
    tabSql: "Query",
    checksCaption: "{shown} visible checks of {total} in the run.",
    emptyChecks: "No checks match these filters.",
    colDate: "Date",
    colCheck: "Check",
    colTable: "Table",
    colSeverity: "Severity",
    colStatus: "Status",
    colMetric: "Metric",
    colRows: "Count",
    samples: "Sample rows (15 at most)",
    noSamples: "This result did not keep sample rows.",
    incidentsCaption: "{caught} of {total} catalog defects were caught at the requested row minimum.",
    emptyIncidents: "No incidents match these filters.",
    colDefect: "Defect",
    colObserved: "Observed rows",
    colMinimum: "Minimum",
    colResult: "Result",
    caught: "caught",
    missed: "missed",
    lineageIntro:
      "Edges come from checks/rutanorte_daily.yaml. Raw nodes are declared only. The generator does not materialize them. Text color follows the run on this screen.",
    declared: "declared",
    failDays: "fails on {count} days",
    cleanDays: "no failures",
    mermaidSummary: "Mermaid text for the same graph",
    rulesTitle: "How a day is scored",
    rulesScore:
      "Score = 100 × weight of passing checks / weight of scored checks. A skipped check, while the median or the calibration window is still filling, stays out of the denominator.",
    rulesSla:
      "The day passes when the score is at least {line} and no critical check failed. The same rule is applied per table. Weights: critical 5, high 3, medium 2, low 1.",
    rulesDrift:
      "Volume uses the previous 14 day median. PSI uses the first 14 business dates as a fixed baseline, so an incident cannot leak into the reference.",
    rulesId:
      "RFC, CURP, email, and phone are checked for shape, including a real calendar date inside RFC and CURP. They are not SAT or RENAPO checksums, and nothing is sent out of this browser.",
    rulesData:
      "RutaNorte Paqueteria is fictitious. People, hubs, shipments, and scans are synthetic, seed 42, from 1 Sep 2026 through 15 Oct 2026.",
    sqlIntro: "The query runs in the same DuckDB that just scored the checks. Read only.",
    sqlRun: "Run this query",
    sqlRows: "{shown} rows.",
    sqlTruncated: "Showing the first {shown} rows.",
    sqlEmpty: "The query returned no rows.",
    presetChannel: "Show the 13 Oct channel mix",
    presetEmail: "Show the 10 Oct null emails",
    presetLate: "Show the 15 Oct scan load",
    errEmpty: "Write a query.",
    errMulti: "One statement only.",
    errSelect: "SELECT or WITH only.",
    errForbidden: "This query is not allowed. The warehouse is read only.",
    errSql: "DuckDB rejected the query: {message}",
    pass: "pass",
    fail: "fail",
    skipped: "skipped",
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
    nullMetric: "{rate} null",
    invalidMetric: "{rate} invalid",
    dupMetric: "{count} duplicates",
    rejectMetric: "{count} rejected",
    orphanMetric: "{count} orphans",
    lateMetric: "{hours} h",
    onTimeMetric: "on time",
    volumeMetric: "{rate} vs median",
    psiMetric: "PSI {value}",
    goldenMetric: "{count} metrics",
    rowsPair: "{failed} / {total}",
    skipVolume: "Skipped. Need {window} prior days and have {have}.",
    skipDrift: "Skipped. The first {window} dates calibrate PSI and this is day {day}.",
    completenessFail: "Null rate {rate} ({failed} of {total} rows) is above {threshold}.",
    completenessPass: "Null rate {rate} ({failed} of {total} rows) is within {threshold}.",
    validityFail: "{failed} of {present} non blank values fail {format}. Rate {rate}, maximum {threshold}.",
    validityPass: "{format} invalid rate {rate} is within {threshold}.",
    uniqueFail: "{failed} rows sit in duplicate {columns} groups.",
    uniquePass: "{columns} is unique across {total} rows.",
    acceptedFail: "{failed} of {total} rows fall outside ({allowed}).",
    acceptedPass: "All {total} rows are inside ({allowed}).",
    refFail: "{failed} of {total} rows reference a missing {ref}.",
    refPass: "Every row references {ref}.",
    freshFail: "Arrived {hours} hours after the deadline (loaded_at {loaded}, deadline {deadline}).",
    freshPass: "Arrived {hours} hours before the deadline (loaded_at {loaded}, deadline {deadline}).",
    freshMissing: "No {timestamp} value for this date.",
    volumeFail:
      "Row count {count} deviates {deviation} from the {window} day median ({center}). The limit is {limit}.",
    volumePass:
      "Row count {count} deviates {deviation} from the {window} day median ({center}), within {limit}.",
    driftFail: "PSI {psi} exceeds {threshold} for {column}, against the first {window} dates.",
    driftPass: "PSI {psi} is within {threshold} for {column}, against the first {window} dates.",
    goldenPass: "All {count} golden metrics match.",
    goldenMissing: "{name} is missing (actual {actual}, expected {expected}).",
    goldenAbs: "{name} actual {actual}, expected {expected} (absolute difference {diff}, tolerance {tolerance}).",
    colophon:
      "IBM Plex Sans, designed by IBM for dense technical interfaces. Tabular figures keep scores and counts aligned. IBM Plex Mono is limited to identifiers, SQL, and samples. Accent #0C5C58, the ink of a route stamp, one color. #7A2424 is reserved for the word fail.",
    local: "The local Streamlit room remains at dashboard/app.py.",
    synthetic: "Synthetic data. RutaNorte is not a real company.",
  },
};

const CHECKS_ES = {
  customers_customer_id_unique: "El customer_id es el grano de la partición de altas.",
  customers_email_completeness: "El correo es obligatorio en cada cliente nuevo.",
  customers_email_validity: "Un correo no vacío tiene que parecer un correo.",
  customers_phone_completeness: "El teléfono es obligatorio en cada cliente nuevo.",
  customers_phone_validity: "El teléfono usa +52 y 10 dígitos.",
  customers_rfc_validity: "Forma de RFC de persona física, con una fecha real. No es el dígito del SAT.",
  customers_curp_validity: "Forma de CURP, con sexo, estado y una fecha real. No es el dígito de RENAPO.",
  customers_segment_values: "El segmento es residential o commercial.",
  customers_status_values: "El estado del cliente es active o inactive.",
  customers_freshness: "La partición de altas vence a las 08:00 de la mañana siguiente.",
  customers_volume_anomaly: "Las altas del día se quedan a 35% o menos de la mediana de 14 días.",
  customers_segment_drift: "La mezcla de segmento se compara con las primeras 14 fechas.",
  scans_scan_id_unique: "El scan_id es único dentro de la fecha.",
  scans_customer_completeness: "Cada escaneo nombra un cliente.",
  scans_barcode_completeness: "Cada escaneo tiene código de barras.",
  scans_customer_fk: "El cliente del escaneo existe en customers.",
  scans_event_values: "El evento es pickup, hub_in o out_for_delivery.",
  scans_freshness: "La partición de escaneos vence a las 08:00 de la mañana siguiente.",
  scans_volume_anomaly: "El volumen de escaneos se queda a 35% o menos de la mediana móvil.",
  shipments_shipment_id_unique: "El shipment_id es único dentro de la fecha.",
  shipments_weight_completeness: "Cada envío tiene peso en gramos.",
  shipments_customer_fk: "El envío apunta a un cliente conocido.",
  shipments_hub_fk: "El envío apunta a una sucursal registrada.",
  shipments_channel_values: "El canal es home, branch, locker o counter.",
  shipments_status_values: "El estado es delivered, in_transit, returned o exception.",
  shipments_country_values: "Esta red origina envíos en MX.",
  shipments_freshness: "La partición de envíos vence a las 08:00 de la mañana siguiente.",
  shipments_volume_anomaly: "El conteo diario se queda a 35% o menos de la mediana de 14 días.",
  shipments_channel_drift: "La mezcla de canal se compara con las primeras 14 fechas (PSI).",
  shipments_weight_drift: "La forma del peso se compara con la ventana de calibración (PSI en cuantiles).",
  kpis_business_date_unique: "El mart publica una fila por fecha.",
  kpis_shipment_count_completeness: "El conteo publicado viene poblado.",
  kpis_weight_completeness: "El peso publicado viene poblado.",
  kpis_golden_reconciliation: "Los totales publicados igualan el archivo golden de operación.",
  kpis_freshness: "La partición del mart vence a las 08:00 de la mañana siguiente.",
  hubs_hub_id_unique: "El hub_id es único en el padrón.",
  hubs_rfc_validity: "El RFC de la sucursal usa la forma de persona moral. No es el dígito del SAT.",
  hubs_branch_code_completeness: "Cada sucursal tiene clave.",
  hubs_city_completeness: "Cada sucursal tiene ciudad.",
};

const DEFECTS_ES = {
  "DEF-SHIPMENT-DUP": "Cinco shipment_id se clonaron, así que cada una de esas llaves aparece dos veces.",
  "DEF-GOLDEN-SHIPMENT-DUP": "Los envíos clonados mueven el conteo y el peso publicados fuera del golden.",
  "DEF-WEIGHT-DRIFT": "Ese día cada envío se reescribió a un peso micro de 1.00 a 9.50 g.",
  "DEF-GOLDEN-WEIGHT": "El día de peso micro conserva el conteo y rompe el peso golden.",
  "DEF-EMAIL-NULL": "25 clientes nuevos se cargaron con correo nulo.",
  "DEF-RFC-FORMAT": "12 clientes nuevos tienen un RFC que no es forma de persona física.",
  "DEF-CURP-FORMAT": "10 clientes nuevos tienen un CURP que no cumple el patrón estructural.",
  "DEF-EMAIL-FORMAT": "8 clientes nuevos tienen un correo no nulo que no es un correo.",
  "DEF-PHONE-FORMAT": "8 clientes nuevos tienen un teléfono que no es +52 más 10 dígitos.",
  "DEF-SEGMENT": "4 clientes nuevos quedaron con un segmento fuera de la lista aceptada.",
  "DEF-SEGMENT-DRIFT": "El segmento desconocido es una categoría nueva, así que la mezcla de altas se separa de la calibración.",
  "DEF-CUST-DUP": "6 customer_id se insertaron dos veces en la misma fecha de alta.",
  "DEF-SHIPMENT-ORPHAN-CUSTOMER": "15 envíos apuntan a un customer_id que nunca se registró.",
  "DEF-SHIPMENT-ORPHAN-HUB": "7 envíos apuntan al hub_id HUB-MISSING.",
  "DEF-SCAN-ORPHAN": "5 escaneos apuntan a un customer_id que no existe.",
  "DEF-GOLDEN-ORPHAN": "Los envíos huérfanos mueven el total diario publicado fuera del golden.",
  "DEF-VOLUME": "El archivo del día conservó 200 de los 1,000 envíos habituales.",
  "DEF-GOLDEN-VOLUME": "El archivo adelgazado rompe el conteo golden y el peso golden.",
  "DEF-CHANNEL-DRIFT": "La mezcla de canal se reescribió a 80% counter, contra una base de 5% counter.",
  "DEF-SCAN-FRESHNESS": "La partición de escaneos de la fecha de corte se selló 12 horas después de su límite.",
};

const NODES_ES = {
  raw_customer_signups: "Altas crudas",
  raw_scan_events: "Escaneos crudos",
  raw_hub_registry: "Sucursales crudas",
  raw_shipment_events: "Envíos crudos",
  customers: "customers",
  tracking_scans: "tracking_scans",
  hubs: "hubs",
  shipments: "shipments",
  daily_route_kpis: "daily_route_kpis",
};

const MONTHS = {
  es: ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
};

export function t(lang, key, vars = {}) {
  const template = STRINGS[lang]?.[key] ?? STRINGS.es[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ""));
}

export function formatCount(value, lang) {
  return Number(value).toLocaleString(lang === "en" ? "en-US" : "es-MX");
}

export function formatScore(value) {
  return Number(value).toFixed(2);
}

export function formatPct(rate) {
  return `${(Number(rate) * 100).toFixed(2)}%`;
}

export function formatDay(iso, lang) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-");
  return `${Number(day)} ${MONTHS[lang][Number(month) - 1]} ${year}`;
}

export function statusLabel(status, lang) {
  return t(lang, status === "fail" || status === "pass" || status === "skipped" ? status : "fail");
}

export function severityLabel(severity, lang) {
  return t(lang, severity);
}

export function checkDescription(id, fallback, lang) {
  if (lang === "es" && CHECKS_ES[id]) return CHECKS_ES[id];
  return fallback;
}

export function defectDescription(id, fallback, lang) {
  if (lang === "es" && DEFECTS_ES[id]) return DEFECTS_ES[id];
  return fallback;
}

export function nodeLabel(node, lang) {
  if (lang === "es" && NODES_ES[node.id]) return NODES_ES[node.id];
  return node.label || node.id;
}

function money(name, value) {
  if (value == null || value === "") return "null";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (String(name).includes("weight")) return number.toFixed(2);
  if (Math.abs(number - Math.round(number)) < 1e-6) return String(Math.round(number));
  return number.toFixed(2);
}

export function describe(result, lang) {
  const detail = result.detail || {};
  if (result.status === "skipped" && result.check_type === "volume_anomaly") {
    return t(lang, "skipVolume", detail);
  }
  if (result.status === "skipped") return t(lang, "skipDrift", { window: detail.window, day: detail.index });
  if (result.check_type === "completeness") {
    return t(lang, result.status === "fail" ? "completenessFail" : "completenessPass", {
      rate: formatPct(detail.rate),
      failed: detail.failed,
      total: detail.total,
      threshold: formatPct(detail.threshold),
    });
  }
  if (result.check_type === "validity") {
    return t(lang, result.status === "fail" ? "validityFail" : "validityPass", {
      failed: detail.failed,
      present: detail.present,
      format: detail.format,
      rate: formatPct(detail.rate),
      threshold: formatPct(detail.threshold),
    });
  }
  if (result.check_type === "uniqueness") {
    return t(lang, result.status === "fail" ? "uniqueFail" : "uniquePass", detail);
  }
  if (result.check_type === "accepted_values") {
    return t(lang, result.status === "fail" ? "acceptedFail" : "acceptedPass", detail);
  }
  if (result.check_type === "referential_integrity") {
    return t(lang, result.status === "fail" ? "refFail" : "refPass", detail);
  }
  if (result.check_type === "freshness") {
    if (detail.lateness == null) return t(lang, "freshMissing", detail);
    const hours = Math.abs(detail.lateness).toFixed(2);
    return t(lang, result.status === "fail" ? "freshFail" : "freshPass", { ...detail, hours });
  }
  if (result.check_type === "volume_anomaly") {
    return t(lang, result.status === "fail" ? "volumeFail" : "volumePass", {
      count: detail.count,
      deviation: formatPct(detail.deviation),
      window: detail.window,
      center: Number(detail.center).toFixed(0),
      limit: formatPct(detail.limit),
    });
  }
  if (result.check_type === "distribution_drift") {
    return t(lang, result.status === "fail" ? "driftFail" : "driftPass", {
      psi: Number(detail.psi).toFixed(4),
      threshold: Number(detail.threshold).toFixed(2),
      column: detail.column,
      window: detail.window,
    });
  }
  if (result.check_type === "golden_reconciliation") {
    if (result.status !== "fail") return t(lang, "goldenPass", { count: detail.metrics });
    return (detail.breaches || [])
      .map((breach) => {
        if (breach.missing) {
          return t(lang, "goldenMissing", {
            name: breach.name,
            actual: money(breach.name, breach.actual),
            expected: money(breach.name, breach.expected),
          });
        }
        return t(lang, "goldenAbs", {
          name: breach.name,
          actual: money(breach.name, breach.actual),
          expected: money(breach.name, breach.expected),
          diff: breach.kind === "pct" ? formatPct(breach.difference) : money(breach.name, breach.difference),
          tolerance: breach.tolerance,
        });
      })
      .join(" ");
  }
  return result.check_id;
}

export function metricCell(result, lang) {
  const detail = result.detail || {};
  if (result.metric_value == null && result.status === "skipped") return statusLabel("skipped", lang);
  if (result.check_type === "completeness") return t(lang, "nullMetric", { rate: formatPct(detail.rate ?? result.metric_value) });
  if (result.check_type === "validity") return t(lang, "invalidMetric", { rate: formatPct(detail.rate ?? result.metric_value) });
  if (result.check_type === "uniqueness") return t(lang, "dupMetric", { count: result.metric_value });
  if (result.check_type === "accepted_values") return t(lang, "rejectMetric", { count: result.metric_value });
  if (result.check_type === "referential_integrity") return t(lang, "orphanMetric", { count: result.metric_value });
  if (result.check_type === "freshness") {
    if (result.metric_value == null) return statusLabel(result.status, lang);
    if (result.status === "pass") return t(lang, "onTimeMetric");
    return t(lang, "lateMetric", { hours: Number(result.metric_value).toFixed(2) });
  }
  if (result.check_type === "volume_anomaly") {
    return t(lang, "volumeMetric", { rate: formatPct(result.metric_value || 0) });
  }
  if (result.check_type === "distribution_drift") {
    return t(lang, "psiMetric", { value: Number(result.metric_value).toFixed(4) });
  }
  if (result.check_type === "golden_reconciliation") {
    return t(lang, "goldenMetric", { count: result.metric_value });
  }
  return String(result.metric_value ?? "");
}

export const SQL_PRESETS = {
  channel: `SELECT channel, count(*) AS shipments
FROM shipments
WHERE business_date = DATE '2026-10-13'
GROUP BY channel
ORDER BY shipments DESC`,
  email: `SELECT customer_id, email, phone, rfc, curp, segment
FROM customers
WHERE created_date = DATE '2026-10-10'
  AND email IS NULL
ORDER BY customer_id`,
  late: `SELECT business_date, max(loaded_at) AS loaded_at, count(*) AS scans
FROM tracking_scans
WHERE business_date = DATE '2026-10-15'
GROUP BY business_date`,
};
