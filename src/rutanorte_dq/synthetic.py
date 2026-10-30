"""Build the fictitious RutaNorte Paqueteria warehouse and inject a labeled defect catalog.

Every person, hub, courier, RFC, CURP, shipment, and tracking scan in this module
is synthetic. The generator is deterministic for a given seed. It writes a golden
daily-total file from the clean shipments, then applies the defects, then builds
``daily_route_kpis`` so the mart inherits upstream damage.
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from rutanorte_dq.identifiers import (
    CURP_STATES,
    valid_curp,
    valid_email,
    valid_phone_mx,
    valid_rfc_fisica,
    valid_rfc_moral,
)
from rutanorte_dq.sql_safety import quote_ident
from rutanorte_dq.warehouse import connect

WINDOW_START = date(2026, 9, 1)
WINDOW_END = date(2026, 10, 15)
DATE_TXN_DUP = date(2026, 10, 7)
DATE_AMOUNT = date(2026, 10, 8)
DATE_CUSTOMERS = date(2026, 10, 10)
DATE_ORPHANS = date(2026, 10, 11)
DATE_VOLUME = date(2026, 10, 12)
DATE_CHANNEL = date(2026, 10, 13)
DATE_FRESHNESS = date(2026, 10, 15)

CUSTOMERS_PER_DAY = 80
COHORTS = 5
COHORT_SIZE = 200
CLEAN_SHIPMENTS_PER_DAY = COHORTS * COHORT_SIZE
CLEAN_DAILY_WEIGHT_G = Decimal("1502300.00")
HUB_COUNT = 120
DEADLINE_HOURS = 32
ON_TIME_HOURS = 29
LATE_HOURS = 44

GIVEN_NAMES = (
    "Ana",
    "Luis",
    "Mateo",
    "Sofia",
    "Regina",
    "Diego",
    "Camila",
    "Javier",
    "Renata",
    "Emiliano",
    "Paula",
    "Hugo",
    "Irene",
    "Oscar",
    "Nora",
    "Bruno",
    "Elena",
    "Raul",
    "Teresa",
    "Ivan",
    "Lucia",
    "Pedro",
    "Clara",
    "Andres",
    "Rosa",
    "Mario",
    "Eva",
    "Sara",
    "Tomas",
    "Julia",
)
SURNAMES = (
    "Garcia",
    "Hernandez",
    "Lopez",
    "Martinez",
    "Gonzalez",
    "Ramirez",
    "Flores",
    "Torres",
    "Rivera",
    "Gomez",
    "Diaz",
    "Cruz",
    "Morales",
    "Reyes",
    "Ortiz",
    "Vargas",
    "Castillo",
    "Romero",
    "Aguilar",
    "Mendoza",
    "Herrera",
    "Medina",
    "Rojas",
    "Silva",
    "Navarro",
    "Campos",
    "Guerrero",
    "Vega",
    "Sandoval",
    "Paredes",
)
CONSONANTS = "BCDFGHJKLMNPQRSTVWXYZ"
HOMOCLAVE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

CHANNEL_PLAN = (("home", 110), ("branch", 50), ("locker", 30), ("counter", 10))
WEIGHT_PLAN = (
    (Decimal("100.00"), 40),
    (Decimal("250.00"), 50),
    (Decimal("499.00"), 40),
    (Decimal("1200.00"), 30),
    (Decimal("3500.00"), 24),
    (Decimal("9000.00"), 16),
)
STATUS_PLAN = (("delivered", 180), ("in_transit", 12), ("returned", 6), ("exception", 2))
SEGMENT_PLAN = ("residential",) * 56 + ("commercial",) * 24
CUSTOMER_STATUS_PLAN = ("active",) * 76 + ("inactive",) * 4
SCAN_EVENT_PLAN = ("pickup",) * 70 + ("hub_in",) * 6 + ("out_for_delivery",) * 4
DEVICE_PLAN = ("handheld",) * 70 + ("gate",) * 10
COURIER_NAMES = ("Sol", "Bruma", "Nube", "Cedra", "Duna", "Pino", "Loma", "Rio")

HUB_COLUMNS = (
    "hub_id",
    "hub_name",
    "branch_code",
    "city",
    "state_code",
    "rfc",
    "onboarded_date",
    "loaded_at",
)
CUSTOMER_COLUMNS = (
    "customer_id",
    "created_date",
    "full_name",
    "email",
    "phone",
    "rfc",
    "curp",
    "state_code",
    "segment",
    "status",
    "loaded_at",
)
SCAN_COLUMNS = (
    "scan_id",
    "customer_id",
    "business_date",
    "device_type",
    "barcode",
    "scan_event",
    "dwell_minutes",
    "scanned_at",
    "relayed_at",
    "loaded_at",
)
SHIPMENT_COLUMNS = (
    "shipment_id",
    "business_date",
    "customer_id",
    "hub_id",
    "courier_name",
    "weight_g",
    "country_code",
    "channel",
    "status",
    "shipped_at",
    "loaded_at",
)

EXPECTED_DEFECTS = (
    {
        "id": "DEF-SHIPMENT-DUP",
        "business_date": DATE_TXN_DUP.isoformat(),
        "table": "shipments",
        "check_id": "shipments_shipment_id_unique",
        "defect_type": "uniqueness",
        "min_failed_rows": 10,
        "description": "Five shipment ids were cloned, so each of those keys appears twice.",
    },
    {
        "id": "DEF-GOLDEN-SHIPMENT-DUP",
        "business_date": DATE_TXN_DUP.isoformat(),
        "table": "daily_route_kpis",
        "check_id": "kpis_golden_reconciliation",
        "defect_type": "golden_reconciliation",
        "min_failed_rows": 1,
        "description": "Cloned shipments move the published daily count and weight off the golden file.",
    },
    {
        "id": "DEF-WEIGHT-DRIFT",
        "business_date": DATE_AMOUNT.isoformat(),
        "table": "shipments",
        "check_id": "shipments_weight_drift",
        "defect_type": "distribution_drift",
        "min_failed_rows": CLEAN_SHIPMENTS_PER_DAY,
        "description": "Every shipment that day was rewritten to a 1.00-9.50 gram micro weight.",
    },
    {
        "id": "DEF-GOLDEN-WEIGHT",
        "business_date": DATE_AMOUNT.isoformat(),
        "table": "daily_route_kpis",
        "check_id": "kpis_golden_reconciliation",
        "defect_type": "golden_reconciliation",
        "min_failed_rows": 1,
        "description": "The micro-weight day keeps the row count and breaks the golden weight.",
    },
    {
        "id": "DEF-EMAIL-NULL",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_email_completeness",
        "defect_type": "completeness",
        "min_failed_rows": 25,
        "description": "25 new customers were loaded with a null email.",
    },
    {
        "id": "DEF-RFC-FORMAT",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_rfc_validity",
        "defect_type": "validity",
        "min_failed_rows": 12,
        "description": "12 new customers have an RFC that is not a persona fisica format.",
    },
    {
        "id": "DEF-CURP-FORMAT",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_curp_validity",
        "defect_type": "validity",
        "min_failed_rows": 10,
        "description": "10 new customers have a CURP that fails the structural pattern.",
    },
    {
        "id": "DEF-EMAIL-FORMAT",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_email_validity",
        "defect_type": "validity",
        "min_failed_rows": 8,
        "description": "8 new customers have a non-null email that is not an email address.",
    },
    {
        "id": "DEF-PHONE-FORMAT",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_phone_validity",
        "defect_type": "validity",
        "min_failed_rows": 8,
        "description": "8 new customers have a phone number that is not +52 plus 10 digits.",
    },
    {
        "id": "DEF-SEGMENT",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_segment_values",
        "defect_type": "accepted_values",
        "min_failed_rows": 4,
        "description": "4 new customers were tagged with a segment outside the accepted list.",
    },
    {
        "id": "DEF-SEGMENT-DRIFT",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_segment_drift",
        "defect_type": "distribution_drift",
        "min_failed_rows": CUSTOMERS_PER_DAY + 6,
        "description": (
            "The unknown segment is a new category, so the signup mix drifts from the calibration window."
        ),
    },
    {
        "id": "DEF-CUST-DUP",
        "business_date": DATE_CUSTOMERS.isoformat(),
        "table": "customers",
        "check_id": "customers_customer_id_unique",
        "defect_type": "uniqueness",
        "min_failed_rows": 12,
        "description": "6 customer ids were inserted twice on the same signup date.",
    },
    {
        "id": "DEF-SHIPMENT-ORPHAN-CUSTOMER",
        "business_date": DATE_ORPHANS.isoformat(),
        "table": "shipments",
        "check_id": "shipments_customer_fk",
        "defect_type": "referential_integrity",
        "min_failed_rows": 15,
        "description": "15 shipments reference a customer id that was never registered.",
    },
    {
        "id": "DEF-SHIPMENT-ORPHAN-HUB",
        "business_date": DATE_ORPHANS.isoformat(),
        "table": "shipments",
        "check_id": "shipments_hub_fk",
        "defect_type": "referential_integrity",
        "min_failed_rows": 7,
        "description": "7 shipments reference hub id HUB-MISSING.",
    },
    {
        "id": "DEF-SCAN-ORPHAN",
        "business_date": DATE_ORPHANS.isoformat(),
        "table": "tracking_scans",
        "check_id": "scans_customer_fk",
        "defect_type": "referential_integrity",
        "min_failed_rows": 5,
        "description": "5 tracking scans reference a customer id that does not exist.",
    },
    {
        "id": "DEF-GOLDEN-ORPHAN",
        "business_date": DATE_ORPHANS.isoformat(),
        "table": "daily_route_kpis",
        "check_id": "kpis_golden_reconciliation",
        "defect_type": "golden_reconciliation",
        "min_failed_rows": 1,
        "description": "The extra orphan shipments move the published daily total off the golden file.",
    },
    {
        "id": "DEF-VOLUME",
        "business_date": DATE_VOLUME.isoformat(),
        "table": "shipments",
        "check_id": "shipments_volume_anomaly",
        "defect_type": "volume_anomaly",
        "min_failed_rows": 800,
        "description": "The shipment file for the day kept 200 of the usual 1,000 shipments.",
    },
    {
        "id": "DEF-GOLDEN-VOLUME",
        "business_date": DATE_VOLUME.isoformat(),
        "table": "daily_route_kpis",
        "check_id": "kpis_golden_reconciliation",
        "defect_type": "golden_reconciliation",
        "min_failed_rows": 1,
        "description": "The thinned shipment file breaks both the golden count and the golden weight.",
    },
    {
        "id": "DEF-CHANNEL-DRIFT",
        "business_date": DATE_CHANNEL.isoformat(),
        "table": "shipments",
        "check_id": "shipments_channel_drift",
        "defect_type": "distribution_drift",
        "min_failed_rows": CLEAN_SHIPMENTS_PER_DAY,
        "description": "Channel mix was rewritten to 80% counter against a 5% counter baseline.",
    },
    {
        "id": "DEF-SCAN-FRESHNESS",
        "business_date": DATE_FRESHNESS.isoformat(),
        "table": "tracking_scans",
        "check_id": "scans_freshness",
        "defect_type": "freshness",
        "min_failed_rows": CUSTOMERS_PER_DAY,
        "description": "The tracking-scan partition for the as-of date was stamped 12 hours after its deadline.",
    },
)


def generate(
    db_path: Path,
    golden_path: Path,
    ground_truth_path: Path,
    *,
    seed: int = 42,
) -> dict:
    """Create the warehouse, golden file, and ground-truth catalog."""
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(db_path)
    try:
        _create_tables(connection)
        rng = random.Random(seed)
        hubs = _hub_rows(rng)
        customers, scan_rows, shipments = _activity_rows(rng)
        _bulk_insert(connection, "hubs", HUB_COLUMNS, hubs)
        _bulk_insert(connection, "customers", CUSTOMER_COLUMNS, customers)
        _bulk_insert(connection, "tracking_scans", SCAN_COLUMNS, scan_rows)
        _bulk_insert(connection, "shipments", SHIPMENT_COLUMNS, shipments)
        _write_golden(connection, golden_path)
        _inject_defects(connection)
        _assert_injections(connection, golden_path)
        _create_kpis(connection)
        _write_ground_truth(ground_truth_path, seed)
        summary = {
            "seed": seed,
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "days": _days_between(WINDOW_START, WINDOW_END),
            "hubs": _count(connection, "hubs"),
            "customers": _count(connection, "customers"),
            "tracking_scans": _count(connection, "tracking_scans"),
            "shipments": _count(connection, "shipments"),
            "daily_route_kpis": _count(connection, "daily_route_kpis"),
            "defects": len(EXPECTED_DEFECTS),
            "clean_shipments_per_day": CLEAN_SHIPMENTS_PER_DAY,
            "clean_daily_weight_g": str(CLEAN_DAILY_WEIGHT_G),
            "db_path": str(db_path),
            "golden_path": str(golden_path),
            "ground_truth_path": str(ground_truth_path),
        }
        return summary
    finally:
        connection.close()


def _days_between(start: date, end: date) -> int:
    return (end - start).days + 1


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _on_time(day: date) -> datetime:
    return datetime.combine(day, time.min) + timedelta(hours=ON_TIME_HOURS)


def _count(connection, table: str) -> int:
    return int(connection.execute(f"SELECT count(*) FROM {quote_ident(table)}").fetchone()[0])


def _create_tables(connection) -> None:
    connection.execute("DROP TABLE IF EXISTS daily_route_kpis")
    connection.execute("DROP TABLE IF EXISTS shipments")
    connection.execute("DROP TABLE IF EXISTS tracking_scans")
    connection.execute("DROP TABLE IF EXISTS customers")
    connection.execute("DROP TABLE IF EXISTS hubs")
    connection.execute(
        """
        CREATE TABLE hubs (
            hub_id VARCHAR,
            hub_name VARCHAR,
            branch_code VARCHAR,
            city VARCHAR,
            state_code VARCHAR,
            rfc VARCHAR,
            onboarded_date DATE,
            loaded_at TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE customers (
            customer_id VARCHAR,
            created_date DATE,
            full_name VARCHAR,
            email VARCHAR,
            phone VARCHAR,
            rfc VARCHAR,
            curp VARCHAR,
            state_code VARCHAR,
            segment VARCHAR,
            status VARCHAR,
            loaded_at TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE tracking_scans (
            scan_id VARCHAR,
            customer_id VARCHAR,
            business_date DATE,
            device_type VARCHAR,
            barcode VARCHAR,
            scan_event VARCHAR,
            dwell_minutes INTEGER,
            scanned_at TIMESTAMP,
            relayed_at TIMESTAMP,
            loaded_at TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE shipments (
            shipment_id VARCHAR,
            business_date DATE,
            customer_id VARCHAR,
            hub_id VARCHAR,
            courier_name VARCHAR,
            weight_g DECIMAL(12, 2),
            country_code VARCHAR,
            channel VARCHAR,
            status VARCHAR,
            shipped_at TIMESTAMP,
            loaded_at TIMESTAMP
        )
        """
    )


def _create_kpis(connection) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE daily_route_kpis AS
        SELECT
            business_date,
            count(*)::BIGINT AS shipment_count,
            count(DISTINCT customer_id)::BIGINT AS active_customers,
            sum(weight_g)::DECIMAL(18, 2) AS weight_g,
            count(*) FILTER (WHERE status = 'delivered')::BIGINT AS delivered_shipment_count,
            max(loaded_at) AS loaded_at
        FROM shipments
        GROUP BY business_date
        ORDER BY business_date
        """
    )


def _hub_rows(rng: random.Random) -> list[tuple]:
    prefixes = (
        "Hub",
        "Patio",
        "Base",
        "Anden",
        "Bodega",
        "Centro",
        "Puerta",
        "Rampa",
        "Muelle",
        "Nave",
        "Caseta",
        "Deposito",
    )
    suffixes = (
        "Luz Norte",
        "Bruma",
        "Del Valle",
        "Obregon",
        "Tres Rios",
        "La Nube",
        "Volcan",
        "Marea",
        "Del Ajusco",
        "Centla",
    )
    cities = (
        ("Monterrey", "NL"),
        ("Guadalajara", "JC"),
        ("Puebla", "PL"),
        ("Queretaro", "QT"),
        ("Merida", "YN"),
        ("Leon", "GT"),
        ("Tijuana", "BC"),
        ("Toluca", "MC"),
        ("Oaxaca", "OC"),
        ("Morelia", "MN"),
    )
    onboarded = date(2020, 3, 15)
    names = [f"{prefix} {suffix}" for prefix in prefixes for suffix in suffixes]
    if len(names) != HUB_COUNT:
        raise RuntimeError("Hub name plan does not match HUB_COUNT")
    rows = []
    for index, name in enumerate(names, start=1):
        city, state = cities[index % len(cities)]
        rfc = _moral_rfc(name, onboarded, rng)
        rows.append(
            (
                f"HUB-{index:05d}",
                name,
                f"RN-{index % 10:02d}",
                city,
                state,
                rfc,
                onboarded,
                _on_time(WINDOW_START),
            )
        )
    return rows


def _activity_rows(rng: random.Random) -> tuple[list[tuple], list[tuple], list[tuple]]:
    customers: list[tuple] = []
    scan_rows: list[tuple] = []
    shipments: list[tuple] = []
    pool: list[str] = []
    hub_ids = [f"HUB-{index:05d}" for index in range(1, HUB_COUNT + 1)]
    for business_date in _daterange(WINDOW_START, WINDOW_END):
        day_customers = _customers_for_day(business_date, rng)
        customers.extend(day_customers)
        pool.extend(row[0] for row in day_customers)
        scan_rows.extend(_scans_for_customers(day_customers))
        shipments.extend(_shipments_for_day(business_date, pool, hub_ids, rng))
    return customers, scan_rows, shipments


def _customers_for_day(business_date: date, rng: random.Random) -> list[tuple]:
    rows = []
    for index in range(CUSTOMERS_PER_DAY):
        given = rng.choice(GIVEN_NAMES)
        paternal = rng.choice(SURNAMES)
        maternal = rng.choice(SURNAMES)
        birth = _birth_date(business_date, index)
        state = CURP_STATES[index % len(CURP_STATES)]
        sex = "H" if index % 2 == 0 else "M"
        rfc = _rfc_fisica(paternal, maternal, given, birth, rng)
        curp = _curp(paternal, maternal, given, birth, sex, state, rng)
        serial = f"{business_date:%Y%m%d}{index + 1:02d}"
        email = f"{given}.{paternal}.{serial}@example.com".lower()
        phone = _phone(rng)
        if not (
            valid_rfc_fisica(rfc)
            and valid_curp(curp)
            and valid_email(email)
            and valid_phone_mx(phone)
        ):
            raise RuntimeError(f"Clean customer {serial} failed identifier validation")
        customer_id = f"CUS-{business_date:%Y%m%d}-{index + 1:05d}"
        rows.append(
            (
                customer_id,
                business_date,
                f"{given} {paternal} {maternal}",
                email,
                phone,
                rfc,
                curp,
                state,
                SEGMENT_PLAN[index],
                CUSTOMER_STATUS_PLAN[index],
                _on_time(business_date),
            )
        )
    return rows


def _scans_for_customers(customers: list[tuple]) -> list[tuple]:
    rows = []
    for index, customer in enumerate(customers):
        customer_id, business_date = customer[0], customer[1]
        scanned_at = datetime.combine(business_date, time(10, index % 50))
        rows.append(
            (
                f"SCN-{business_date:%Y%m%d}-{index + 1:05d}",
                customer_id,
                business_date,
                DEVICE_PLAN[index],
                f"PKG{business_date:%Y%m%d}{index + 1:05d}",
                SCAN_EVENT_PLAN[index],
                int((index * 17) % 100),
                scanned_at,
                scanned_at + timedelta(hours=4),
                _on_time(business_date),
            )
        )
    return rows


def _shipments_for_day(business_date, pool, hub_ids, rng: random.Random) -> list[tuple]:
    pattern_rng = random.Random(rng.random())
    channels = _expand(CHANNEL_PLAN)
    weights = _expand(WEIGHT_PLAN)
    statuses = _expand(STATUS_PLAN)
    pattern_rng.shuffle(channels)
    pattern_rng.shuffle(weights)
    pattern_rng.shuffle(statuses)
    pattern = list(zip(channels, weights, statuses, strict=True))
    if len(pattern) != COHORT_SIZE:
        raise RuntimeError("Cohort pattern must contain 200 shipments")
    rows = []
    for cohort in range(COHORTS):
        for seq, (channel, weight_g, status) in enumerate(pattern):
            position = cohort * COHORT_SIZE + seq
            rows.append(
                (
                    f"SHP-{business_date:%Y%m%d}-{cohort}-{seq:04d}",
                    business_date,
                    pool[position % len(pool)],
                    hub_ids[position % len(hub_ids)],
                    COURIER_NAMES[position % len(COURIER_NAMES)],
                    weight_g,
                    "MX",
                    channel,
                    status,
                    datetime.combine(business_date, time(8 + (seq % 12), (seq * 3) % 60)),
                    _on_time(business_date),
                )
            )
    return rows


def _expand(plan) -> list:
    values = []
    for value, count in plan:
        values.extend([value] * count)
    return values


def _birth_date(business_date: date, index: int) -> date:
    year = 1975 + ((business_date.toordinal() + index) % 30)
    month = (index % 12) + 1
    day = (index % 27) + 1
    return date(year, month, day)


def _first_internal_vowel(token: str) -> str:
    for char in token[1:]:
        if char in "AEIOU":
            return char
    return "X"


def _first_internal_consonant(token: str) -> str:
    for char in token[1:]:
        if char in CONSONANTS:
            return char
    return "X"


def _rfc_fisica(paternal: str, maternal: str, given: str, birth: date, rng: random.Random) -> str:
    letters = paternal[0] + _first_internal_vowel(paternal) + maternal[0] + given[0]
    homo = "".join(rng.choice(HOMOCLAVE) for _ in range(3))
    return f"{letters}{birth.strftime('%y%m%d')}{homo}"


def _curp(paternal, maternal, given, birth, sex, state, rng: random.Random) -> str:
    letters = paternal[0] + _first_internal_vowel(paternal) + maternal[0] + given[0]
    body = (
        f"{letters}{birth.strftime('%y%m%d')}{sex}{state}"
        f"{_first_internal_consonant(paternal)}"
        f"{_first_internal_consonant(maternal)}"
        f"{_first_internal_consonant(given)}"
    )
    return body + rng.choice(HOMOCLAVE) + str(rng.randint(0, 9))


def _moral_rfc(name: str, onboarded: date, rng: random.Random) -> str:
    letters = "".join(char for char in name.upper() if char.isalpha())
    letters = (letters + "XXX")[:3]
    homo = "".join(rng.choice(HOMOCLAVE) for _ in range(3))
    rfc = f"{letters}{onboarded.strftime('%y%m%d')}{homo}"
    if not valid_rfc_moral(rfc):
        raise RuntimeError(f"Invalid moral RFC generated: {rfc}")
    return rfc


def _phone(rng: random.Random) -> str:
    digits = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(9))
    return "+52" + digits


def _bulk_insert(connection, table: str, columns: tuple[str, ...], rows: list[tuple]) -> None:
    if not rows:
        return
    column_sql = ", ".join(quote_ident(column) for column in columns)
    placeholders = ", ".join(["?"] * len(columns))
    connection.executemany(
        f"INSERT INTO {quote_ident(table)} ({column_sql}) VALUES ({placeholders})",
        rows,
    )


def _write_golden(connection, path: Path) -> None:
    escaped = str(path).replace("'", "''")
    connection.execute(
        f"""
        COPY (
            SELECT business_date,
                   count(*) AS shipment_count,
                   sum(weight_g) AS weight_g_sum
            FROM shipments
            GROUP BY 1
            ORDER BY 1
        ) TO '{escaped}' (HEADER, DELIMITER ',')
        """
    )


def _write_ground_truth(path: Path, seed: int) -> None:
    document = {
        "description": (
            "Labeled defects injected into the synthetic RutaNorte Paqueteria warehouse. "
            "This catalog is the ground truth for precision and recall. "
            "It is produced by rutanorte_dq.synthetic and is not a production incident log."
        ),
        "seed": seed,
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "defects": list(EXPECTED_DEFECTS),
    }
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _inject_defects(connection) -> None:
    _inject_customer_defects(connection)
    _inject_shipment_duplicates(connection)
    _inject_weight_drift(connection)
    _inject_orphans(connection)
    _inject_volume_drop(connection)
    _inject_channel_drift(connection)
    _inject_late_scans(connection)


def _customer_ids(connection, business_date: date, limit: int, offset: int) -> list[str]:
    rows = connection.execute(
        """
        SELECT customer_id
        FROM customers
        WHERE created_date = ?
        ORDER BY customer_id
        LIMIT ? OFFSET ?
        """,
        [business_date, limit, offset],
    ).fetchall()
    return [row[0] for row in rows]


def _inject_customer_defects(connection) -> None:
    before = _count_where(connection, "customers", "created_date = ?", [DATE_CUSTOMERS])
    if before != CUSTOMERS_PER_DAY:
        raise RuntimeError(
            f"Expected {CUSTOMERS_PER_DAY} customers on {DATE_CUSTOMERS}, found {before}"
        )
    _update_ids(connection, "email", None, _customer_ids(connection, DATE_CUSTOMERS, 25, 6))
    _update_ids(connection, "rfc", "BADRFC", _customer_ids(connection, DATE_CUSTOMERS, 12, 31))
    _update_ids(connection, "curp", "NOTACURP", _customer_ids(connection, DATE_CUSTOMERS, 10, 43))
    _update_ids(
        connection, "email", "not-an-email", _customer_ids(connection, DATE_CUSTOMERS, 8, 53)
    )
    _update_ids(connection, "phone", "12345", _customer_ids(connection, DATE_CUSTOMERS, 8, 61))
    _update_ids(connection, "segment", "unknown", _customer_ids(connection, DATE_CUSTOMERS, 4, 69))
    duplicates = connection.execute(
        f"""
        SELECT {", ".join(quote_ident(column) for column in CUSTOMER_COLUMNS)}
        FROM customers
        WHERE created_date = ?
        ORDER BY customer_id
        LIMIT 6
        """,
        [DATE_CUSTOMERS],
    ).fetchall()
    _bulk_insert(connection, "customers", CUSTOMER_COLUMNS, duplicates)


def _update_ids(connection, column: str, value, customer_ids: list[str]) -> None:
    if not customer_ids:
        raise RuntimeError(f"No customer ids selected for {column}")
    connection.executemany(
        f"UPDATE customers SET {quote_ident(column)} = ? WHERE customer_id = ?",
        [(value, customer_id) for customer_id in customer_ids],
    )


def _inject_shipment_duplicates(connection) -> None:
    rows = connection.execute(
        f"""
        SELECT {", ".join(quote_ident(column) for column in SHIPMENT_COLUMNS)}
        FROM shipments
        WHERE business_date = ?
        ORDER BY shipment_id
        LIMIT 5
        """,
        [DATE_TXN_DUP],
    ).fetchall()
    if len(rows) != 5:
        raise RuntimeError("Could not clone 5 shipments")
    _bulk_insert(connection, "shipments", SHIPMENT_COLUMNS, rows)


def _inject_weight_drift(connection) -> None:
    weights = (
        Decimal("1.00"),
        Decimal("2.50"),
        Decimal("5.00"),
        Decimal("8.00"),
        Decimal("9.50"),
    )
    rows = connection.execute(
        "SELECT shipment_id FROM shipments WHERE business_date = ? ORDER BY shipment_id",
        [DATE_AMOUNT],
    ).fetchall()
    if len(rows) != CLEAN_SHIPMENTS_PER_DAY:
        raise RuntimeError("Weight-drift day does not have the clean shipment count")
    connection.executemany(
        "UPDATE shipments SET weight_g = ? WHERE shipment_id = ?",
        [(weights[index % len(weights)], shipment_id) for index, (shipment_id,) in enumerate(rows)],
    )


def _inject_orphans(connection) -> None:
    hub_id = connection.execute("SELECT min(hub_id) FROM hubs").fetchone()[0]
    connection.execute(
        """
        UPDATE shipments
        SET hub_id = 'HUB-MISSING'
        WHERE business_date = ?
          AND shipment_id IN (
              SELECT shipment_id
              FROM shipments
              WHERE business_date = ?
              ORDER BY shipment_id
              LIMIT 7
          )
        """,
        [DATE_ORPHANS, DATE_ORPHANS],
    )
    loaded = _on_time(DATE_ORPHANS)
    orphan_shipments = []
    for index in range(15):
        orphan_shipments.append(
            (
                f"SHP-{DATE_ORPHANS:%Y%m%d}-X-{index:04d}",
                DATE_ORPHANS,
                f"CUS-MISSING-{index:04d}",
                hub_id,
                COURIER_NAMES[index % len(COURIER_NAMES)],
                Decimal("499.00"),
                "MX",
                "home",
                "delivered",
                datetime.combine(DATE_ORPHANS, time(12, index)),
                loaded,
            )
        )
    _bulk_insert(connection, "shipments", SHIPMENT_COLUMNS, orphan_shipments)
    orphan_scans = []
    for index in range(5):
        scanned_at = datetime.combine(DATE_ORPHANS, time(11, index))
        orphan_scans.append(
            (
                f"SCN-ORPHAN-{DATE_ORPHANS:%Y%m%d}-{index:02d}",
                f"CUS-MISSING-SCN-{index:04d}",
                DATE_ORPHANS,
                "handheld",
                f"ORPHANPKG{index:04d}",
                "pickup",
                10,
                scanned_at,
                scanned_at + timedelta(hours=1),
                loaded,
            )
        )
    _bulk_insert(connection, "tracking_scans", SCAN_COLUMNS, orphan_scans)


def _inject_volume_drop(connection) -> None:
    connection.execute(
        """
        DELETE FROM shipments
        WHERE business_date = ?
          AND shipment_id NOT LIKE ?
        """,
        [DATE_VOLUME, f"SHP-{DATE_VOLUME:%Y%m%d}-0-%"],
    )


def _inject_channel_drift(connection) -> None:
    rows = connection.execute(
        "SELECT shipment_id FROM shipments WHERE business_date = ? ORDER BY shipment_id",
        [DATE_CHANNEL],
    ).fetchall()
    if len(rows) != CLEAN_SHIPMENTS_PER_DAY:
        raise RuntimeError("Channel-drift day does not have the clean shipment count")
    assignments = []
    for index, (shipment_id,) in enumerate(rows):
        if index < 800:
            channel = "counter"
        elif index < 900:
            channel = "home"
        elif index < 950:
            channel = "branch"
        else:
            channel = "locker"
        assignments.append((channel, shipment_id))
    connection.executemany(
        "UPDATE shipments SET channel = ? WHERE shipment_id = ?",
        assignments,
    )


def _inject_late_scans(connection) -> None:
    late = datetime.combine(DATE_FRESHNESS, time.min) + timedelta(hours=LATE_HOURS)
    connection.execute(
        "UPDATE tracking_scans SET loaded_at = ? WHERE business_date = ?",
        [late, DATE_FRESHNESS],
    )


def _count_where(connection, table: str, clause: str, params: list) -> int:
    return int(
        connection.execute(
            f"SELECT count(*) FROM {quote_ident(table)} WHERE {clause}",
            params,
        ).fetchone()[0]
    )


def _expect(connection, sql: str, params: list, expected: int, label: str) -> None:
    found = int(connection.execute(sql, params).fetchone()[0])
    if found != expected:
        raise RuntimeError(f"{label}: expected {expected}, found {found}")


def _assert_injections(connection, golden_path: Path) -> None:
    _expect(
        connection,
        "SELECT count(*) FROM customers WHERE created_date = ? AND email IS NULL",
        [DATE_CUSTOMERS],
        25,
        "null emails",
    )
    _expect(
        connection,
        """
        SELECT count(*) FROM customers
        WHERE created_date = ? AND rfc IS NOT NULL AND NOT dq_rfc_fisica(rfc)
        """,
        [DATE_CUSTOMERS],
        12,
        "invalid RFC",
    )
    _expect(
        connection,
        """
        SELECT count(*) FROM customers
        WHERE created_date = ? AND curp IS NOT NULL AND NOT dq_curp(curp)
        """,
        [DATE_CUSTOMERS],
        10,
        "invalid CURP",
    )
    _expect(
        connection,
        """
        SELECT count(*) FROM customers
        WHERE created_date = ?
          AND email IS NOT NULL
          AND length(trim(email)) > 0
          AND NOT dq_email(email)
        """,
        [DATE_CUSTOMERS],
        8,
        "invalid email",
    )
    _expect(
        connection,
        """
        SELECT count(*) FROM customers
        WHERE created_date = ?
          AND phone IS NOT NULL
          AND NOT dq_phone_mx(phone)
        """,
        [DATE_CUSTOMERS],
        8,
        "invalid phone",
    )
    _expect(
        connection,
        "SELECT count(*) FROM customers WHERE created_date = ? AND segment = 'unknown'",
        [DATE_CUSTOMERS],
        4,
        "unknown segment",
    )
    _expect(
        connection,
        """
        SELECT coalesce(sum(c), 0) FROM (
            SELECT count(*) AS c
            FROM customers
            WHERE created_date = ?
            GROUP BY customer_id
            HAVING count(*) > 1
        )
        """,
        [DATE_CUSTOMERS],
        12,
        "duplicate customers",
    )
    _expect(
        connection,
        "SELECT count(*) FROM shipments WHERE business_date = ?",
        [DATE_VOLUME],
        200,
        "volume drop",
    )
    _expect(
        connection,
        "SELECT count(*) FROM shipments WHERE business_date = ? AND channel = 'counter'",
        [DATE_CHANNEL],
        800,
        "counter drift",
    )
    _expect(
        connection,
        "SELECT count(*) FROM shipments WHERE business_date = ? AND weight_g > 10",
        [DATE_AMOUNT],
        0,
        "weight drift",
    )
    late = datetime.combine(DATE_FRESHNESS, time.min) + timedelta(hours=LATE_HOURS)
    found_late = connection.execute(
        "SELECT max(loaded_at) FROM tracking_scans WHERE business_date = ?",
        [DATE_FRESHNESS],
    ).fetchone()[0]
    if found_late != late:
        raise RuntimeError(f"Tracking-scan freshness stamp: expected {late}, found {found_late}")
    with golden_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != _days_between(WINDOW_START, WINDOW_END):
        raise RuntimeError("Golden file does not cover the full window")
    sample = next(row for row in rows if row["business_date"].startswith("2026-09-20"))
    if int(float(sample["shipment_count"])) != CLEAN_SHIPMENTS_PER_DAY:
        raise RuntimeError("Golden count for a clean day is wrong")
    if Decimal(sample["weight_g_sum"]).quantize(Decimal("0.01")) != CLEAN_DAILY_WEIGHT_G:
        raise RuntimeError(
            f"Golden weight for a clean day is {sample['weight_g_sum']}, expected {CLEAN_DAILY_WEIGHT_G}"
        )


__all__ = [
    "CLEAN_DAILY_WEIGHT_G",
    "CLEAN_SHIPMENTS_PER_DAY",
    "EXPECTED_DEFECTS",
    "WINDOW_END",
    "WINDOW_START",
    "generate",
]
