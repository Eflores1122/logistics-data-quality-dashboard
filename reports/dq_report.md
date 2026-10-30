# RutaNorte data-quality report

> Reference implementation for Edgar Flores. RutaNorte Paqueteria is a fictitious Mexican parcel network created for this project. All warehouse rows are synthetic. This report does not describe any employer, client, or production system.

- Suite: `rutanorte_daily`
- Run: `d6662fa52701431f93bc95f028608f8f`
- Run timestamp (UTC): 2026-10-30 19:22:30
- As-of date: 2026-10-15
- SLA: score >= 95
- Critical failure fails the day: yes

## Detection against injected defects

- Injected defects: 20
- Caught: 20
- Missed: 0
- Unexpected failing checks: 0
- Precision: 1.000
- Recall: 1.000
- Row-level recall: 20/20 (1.000)

A defect is caught when its check fails on the injected business date and, where
the catalog sets a minimum, the check counts at least that many offending rows.
Precision is caught defects divided by caught defects plus failing checks that
are not in the catalog.

## Daily SLA

| Date | Score | SLA | Failed checks | Critical failures |
| --- | ---: | --- | ---: | ---: |
| 2026-09-01 | 100.00 | pass | 0 | 0 |
| 2026-09-02 | 100.00 | pass | 0 | 0 |
| 2026-09-03 | 100.00 | pass | 0 | 0 |
| 2026-09-04 | 100.00 | pass | 0 | 0 |
| 2026-09-05 | 100.00 | pass | 0 | 0 |
| 2026-09-06 | 100.00 | pass | 0 | 0 |
| 2026-09-07 | 100.00 | pass | 0 | 0 |
| 2026-09-08 | 100.00 | pass | 0 | 0 |
| 2026-09-09 | 100.00 | pass | 0 | 0 |
| 2026-09-10 | 100.00 | pass | 0 | 0 |
| 2026-09-11 | 100.00 | pass | 0 | 0 |
| 2026-09-12 | 100.00 | pass | 0 | 0 |
| 2026-09-13 | 100.00 | pass | 0 | 0 |
| 2026-09-14 | 100.00 | pass | 0 | 0 |
| 2026-09-15 | 100.00 | pass | 0 | 0 |
| 2026-09-16 | 100.00 | pass | 0 | 0 |
| 2026-09-17 | 100.00 | pass | 0 | 0 |
| 2026-09-18 | 100.00 | pass | 0 | 0 |
| 2026-09-19 | 100.00 | pass | 0 | 0 |
| 2026-09-20 | 100.00 | pass | 0 | 0 |
| 2026-09-21 | 100.00 | pass | 0 | 0 |
| 2026-09-22 | 100.00 | pass | 0 | 0 |
| 2026-09-23 | 100.00 | pass | 0 | 0 |
| 2026-09-24 | 100.00 | pass | 0 | 0 |
| 2026-09-25 | 100.00 | pass | 0 | 0 |
| 2026-09-26 | 100.00 | pass | 0 | 0 |
| 2026-09-27 | 100.00 | pass | 0 | 0 |
| 2026-09-28 | 100.00 | pass | 0 | 0 |
| 2026-09-29 | 100.00 | pass | 0 | 0 |
| 2026-09-30 | 100.00 | pass | 0 | 0 |
| 2026-10-01 | 100.00 | pass | 0 | 0 |
| 2026-10-02 | 100.00 | pass | 0 | 0 |
| 2026-10-03 | 100.00 | pass | 0 | 0 |
| 2026-10-04 | 100.00 | pass | 0 | 0 |
| 2026-10-05 | 100.00 | pass | 0 | 0 |
| 2026-10-06 | 100.00 | pass | 0 | 0 |
| 2026-10-07 | 90.48 | fail | 2 | 2 |
| 2026-10-08 | 93.33 | fail | 2 | 1 |
| 2026-10-09 | 100.00 | pass | 0 | 0 |
| 2026-10-10 | 79.05 | fail | 8 | 1 |
| 2026-10-11 | 80.95 | fail | 4 | 4 |
| 2026-10-12 | 92.38 | fail | 2 | 1 |
| 2026-10-13 | 98.10 | pass | 1 | 0 |
| 2026-10-14 | 100.00 | pass | 0 | 0 |
| 2026-10-15 | 95.90 | fail | 1 | 1 |

## Failing checks

### 2026-10-07 · daily_route_kpis · `kpis_golden_reconciliation`

- Severity: critical
- Metric: metrics_breached = 2 (threshold == 0)
- Offending rows: 2 of 2
- shipment_count actual 1005 expected 1000 (abs diff 5, tolerance 0.0); weight_g_sum actual 1505247.00 expected 1502300.00 (abs diff 2947.00, tolerance 0.01)

Sample:

```
{'metric': 'shipment_count', 'actual': '1005', 'expected': '1000', 'breached': True}
{'metric': 'weight_g_sum', 'actual': '1505247.00', 'expected': '1502300.00', 'breached': True}
```

### 2026-10-07 · shipments · `shipments_shipment_id_unique`

- Severity: critical
- Metric: duplicate_rows = 10 (threshold == 0)
- Offending rows: 10 of 1005
- 10 rows belong to duplicate shipment_id groups

Sample:

```
{'shipment_id': 'SHP-20261007-0-0000', 'business_date': '2026-10-07', 'customer_id': 'CUS-20260901-00001', 'hub_id': 'HUB-00001', 'courier_name': 'Sol', 'weight_g': '1200.00', 'country_code': 'MX', 'channel': 'home', 'status': 'returned', 'shipped_at': '2026-10-07 08:00:00', 'loaded_at': '2026-10-08 05:00:00'}
{'shipment_id': 'SHP-20261007-0-0001', 'business_date': '2026-10-07', 'customer_id': 'CUS-20260901-00002', 'hub_id': 'HUB-00002', 'courier_name': 'Bruma', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'branch', 'status': 'delivered', 'shipped_at': '2026-10-07 09:03:00', 'loaded_at': '2026-10-08 05:00:00'}
{'shipment_id': 'SHP-20261007-0-0002', 'business_date': '2026-10-07', 'customer_id': 'CUS-20260901-00003', 'hub_id': 'HUB-00003', 'courier_name': 'Nube', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'branch', 'status': 'delivered', 'shipped_at': '2026-10-07 10:06:00', 'loaded_at': '2026-10-08 05:00:00'}
{'shipment_id': 'SHP-20261007-0-0003', 'business_date': '2026-10-07', 'customer_id': 'CUS-20260901-00004', 'hub_id': 'HUB-00004', 'courier_name': 'Cedra', 'weight_g': '250.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-07 11:09:00', 'loaded_at': '2026-10-08 05:00:00'}
{'shipment_id': 'SHP-20261007-0-0004', 'business_date': '2026-10-07', 'customer_id': 'CUS-20260901-00005', 'hub_id': 'HUB-00005', 'courier_name': 'Duna', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-07 12:12:00', 'loaded_at': '2026-10-08 05:00:00'}
```

### 2026-10-08 · daily_route_kpis · `kpis_golden_reconciliation`

- Severity: critical
- Metric: metrics_breached = 1 (threshold == 0)
- Offending rows: 1 of 2
- weight_g_sum actual 5200.00 expected 1502300.00 (abs diff 1497100.00, tolerance 0.01)

Sample:

```
{'metric': 'shipment_count', 'actual': '1000', 'expected': '1000', 'breached': False}
{'metric': 'weight_g_sum', 'actual': '5200.00', 'expected': '1502300.00', 'breached': True}
```

### 2026-10-08 · shipments · `shipments_weight_drift`

- Severity: medium
- Metric: psi = 12.9071 (threshold <= 0.25)
- Offending rows: 1000 of 1000
- PSI 12.9071 exceeds 0.25 for weight_g against the first 14 business dates

Sample:

```
{'bin': 1, 'left': None, 'right': 220.00000000002728, 'actual_rows': 1000, 'actual_share': 1.0, 'reference_rows': 2800, 'reference_share': 0.2}
{'bin': 2, 'left': 220.00000000002728, 'right': 250.0, 'actual_rows': 0, 'actual_share': 0.0, 'reference_rows': 3500, 'reference_share': 0.25}
{'bin': 3, 'left': 250.0, 'right': 499.0, 'actual_rows': 0, 'actual_share': 0.0, 'reference_rows': 2800, 'reference_share': 0.2}
{'bin': 4, 'left': 499.0, 'right': 1660.0000000016735, 'actual_rows': 0, 'actual_share': 0.0, 'reference_rows': 2100, 'reference_share': 0.15}
{'bin': 5, 'left': 1660.0000000016735, 'right': None, 'actual_rows': 0, 'actual_share': 0.0, 'reference_rows': 2800, 'reference_share': 0.2}
```

### 2026-10-10 · customers · `customers_curp_validity`

- Severity: high
- Metric: invalid_rate = 0.1163 (threshold <= 0)
- Offending rows: 10 of 86
- 10 of 86 non-blank values fail curp (invalid rate 11.63%, max 0.00%)

Sample:

```
{'customer_id': 'CUS-20261010-00044', 'created_date': '2026-10-10', 'full_name': 'Sofia Vargas Ortiz', 'email': 'sofia.vargas.2026101044@example.com', 'phone': '+524124219738', 'rfc': 'VXOS9708174RR', 'curp': 'NOTACURP', 'state_code': 'GT', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00045', 'created_date': '2026-10-10', 'full_name': 'Mateo Medina Silva', 'email': 'mateo.medina.2026101045@example.com', 'phone': '+523751029583', 'rfc': 'MXSM980918BOQ', 'curp': 'NOTACURP', 'state_code': 'GR', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00046', 'created_date': '2026-10-10', 'full_name': 'Andres Romero Diaz', 'email': 'andres.romero.2026101046@example.com', 'phone': '+529104535135', 'rfc': 'RXDA991019A6N', 'curp': 'NOTACURP', 'state_code': 'HG', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00047', 'created_date': '2026-10-10', 'full_name': 'Lucia Reyes Silva', 'email': 'lucia.reyes.2026101047@example.com', 'phone': '+523916335471', 'rfc': 'RXSL001120MSO', 'curp': 'NOTACURP', 'state_code': 'JC', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00048', 'created_date': '2026-10-10', 'full_name': 'Clara Cruz Vega', 'email': 'clara.cruz.2026101048@example.com', 'phone': '+527417689220', 'rfc': 'CXVC011221QNP', 'curp': 'NOTACURP', 'state_code': 'MC', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-10 · customers · `customers_customer_id_unique`

- Severity: critical
- Metric: duplicate_rows = 12 (threshold == 0)
- Offending rows: 12 of 86
- 12 rows belong to duplicate customer_id groups

Sample:

```
{'customer_id': 'CUS-20261010-00001', 'created_date': '2026-10-10', 'full_name': 'Bruno Gomez Medina', 'email': 'bruno.gomez.2026101001@example.com', 'phone': '+523198951115', 'rfc': 'GXMB840101T05', 'curp': 'GXMB840101HASXXXC7', 'state_code': 'AS', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00002', 'created_date': '2026-10-10', 'full_name': 'Bruno Romero Sandoval', 'email': 'bruno.romero.2026101002@example.com', 'phone': '+529155860264', 'rfc': 'RXSB8502023IP', 'curp': 'RXSB850202MBCXXXD3', 'state_code': 'BC', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00003', 'created_date': '2026-10-10', 'full_name': 'Regina Flores Morales', 'email': 'regina.flores.2026101003@example.com', 'phone': '+526693714787', 'rfc': 'FXMR860303LTV', 'curp': 'FXMR860303HBSXXX68', 'state_code': 'BS', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00004', 'created_date': '2026-10-10', 'full_name': 'Hugo Vega Garcia', 'email': 'hugo.vega.2026101004@example.com', 'phone': '+523784440027', 'rfc': 'VXGH8704047BW', 'curp': 'VXGH870404MCCXXX31', 'state_code': 'CC', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00005', 'created_date': '2026-10-10', 'full_name': 'Eva Rivera Navarro', 'email': 'eva.rivera.2026101005@example.com', 'phone': '+525793666044', 'rfc': 'RXNE8805056QK', 'curp': 'RXNE880505HCLXXXR4', 'state_code': 'CL', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-10 · customers · `customers_email_completeness`

- Severity: high
- Metric: null_rate = 0.2907 (threshold <= 0)
- Offending rows: 25 of 86
- null rate 29.07% (25 of 86 rows) exceeds 0.00%

Sample:

```
{'customer_id': 'CUS-20261010-00007', 'created_date': '2026-10-10', 'full_name': 'Nora Gomez Aguilar', 'email': None, 'phone': '+524733188156', 'rfc': 'GXAN900707027', 'curp': 'GXAN900707HCSXXXS5', 'state_code': 'CS', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00008', 'created_date': '2026-10-10', 'full_name': 'Bruno Diaz Vega', 'email': None, 'phone': '+527579707907', 'rfc': 'DXVB910808SHN', 'curp': 'DXVB910808MCHXXXV4', 'state_code': 'CH', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00009', 'created_date': '2026-10-10', 'full_name': 'Tomas Ortiz Herrera', 'email': None, 'phone': '+522017314127', 'rfc': 'OXHT920909DTX', 'curp': 'OXHT920909HDFXXXV3', 'state_code': 'DF', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00010', 'created_date': '2026-10-10', 'full_name': 'Diego Cruz Aguilar', 'email': None, 'phone': '+528724055525', 'rfc': 'CXAD931010LGL', 'curp': 'CXAD931010MDGXXX95', 'state_code': 'DG', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00011', 'created_date': '2026-10-10', 'full_name': 'Sara Guerrero Martinez', 'email': None, 'phone': '+528526424374', 'rfc': 'GXMS94111154S', 'curp': 'GXMS941111HGTXXX85', 'state_code': 'GT', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-10 · customers · `customers_email_validity`

- Severity: high
- Metric: invalid_rate = 0.1311 (threshold <= 0)
- Offending rows: 8 of 86
- 8 of 61 non-blank values fail email (invalid rate 13.11%, max 0.00%)

Sample:

```
{'customer_id': 'CUS-20261010-00054', 'created_date': '2026-10-10', 'full_name': 'Mateo Romero Reyes', 'email': 'not-an-email', 'phone': '+529875864740', 'rfc': 'RXRM770627KME', 'curp': 'RXRM770627MPLXXXG6', 'state_code': 'PL', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00055', 'created_date': '2026-10-10', 'full_name': 'Tomas Navarro Sandoval', 'email': 'not-an-email', 'phone': '+523755046161', 'rfc': 'NXST780701HJX', 'curp': 'NXST780701HQTXXXW3', 'state_code': 'QT', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00056', 'created_date': '2026-10-10', 'full_name': 'Emiliano Rojas Torres', 'email': 'not-an-email', 'phone': '+529267545769', 'rfc': 'RXTE7908028RD', 'curp': 'RXTE790802MQRXXXO9', 'state_code': 'QR', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00057', 'created_date': '2026-10-10', 'full_name': 'Lucia Hernandez Aguilar', 'email': 'not-an-email', 'phone': '+522956360385', 'rfc': 'HXAL800903SFQ', 'curp': 'HXAL800903HSPXXXI5', 'state_code': 'SP', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00058', 'created_date': '2026-10-10', 'full_name': 'Lucia Diaz Ramirez', 'email': 'not-an-email', 'phone': '+525299678343', 'rfc': 'DXRL81100467L', 'curp': 'DXRL811004MSLXXXM1', 'state_code': 'SL', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-10 · customers · `customers_phone_validity`

- Severity: medium
- Metric: invalid_rate = 0.093 (threshold <= 0)
- Offending rows: 8 of 86
- 8 of 86 non-blank values fail phone_mx (invalid rate 9.30%, max 0.00%)

Sample:

```
{'customer_id': 'CUS-20261010-00062', 'created_date': '2026-10-10', 'full_name': 'Teresa Silva Ortiz', 'email': 'teresa.silva.2026101062@example.com', 'phone': '12345', 'rfc': 'SXOT850208J7V', 'curp': 'SXOT850208MTLXXXU4', 'state_code': 'TL', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00063', 'created_date': '2026-10-10', 'full_name': 'Clara Martinez Rivera', 'email': 'clara.martinez.2026101063@example.com', 'phone': '12345', 'rfc': 'MXRC860309KEW', 'curp': 'MXRC860309HVZXXXQ4', 'state_code': 'VZ', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00064', 'created_date': '2026-10-10', 'full_name': 'Bruno Rivera Hernandez', 'email': 'bruno.rivera.2026101064@example.com', 'phone': '12345', 'rfc': 'RXHB870410TBX', 'curp': 'RXHB870410MYNXXXK7', 'state_code': 'YN', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00065', 'created_date': '2026-10-10', 'full_name': 'Nora Campos Medina', 'email': 'nora.campos.2026101065@example.com', 'phone': '12345', 'rfc': 'CXMN88051125U', 'curp': 'CXMN880511HZSXXXE0', 'state_code': 'ZS', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00066', 'created_date': '2026-10-10', 'full_name': 'Renata Campos Reyes', 'email': 'renata.campos.2026101066@example.com', 'phone': '12345', 'rfc': 'CXRR890612GXC', 'curp': 'CXRR890612MNEXXXR1', 'state_code': 'NE', 'segment': 'commercial', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-10 · customers · `customers_rfc_validity`

- Severity: high
- Metric: invalid_rate = 0.1395 (threshold <= 0)
- Offending rows: 12 of 86
- 12 of 86 non-blank values fail rfc_fisica (invalid rate 13.95%, max 0.00%)

Sample:

```
{'customer_id': 'CUS-20261010-00032', 'created_date': '2026-10-10', 'full_name': 'Clara Reyes Medina', 'email': 'clara.reyes.2026101032@example.com', 'phone': '+524803371421', 'rfc': 'BADRFC', 'curp': 'RXMC850805MZSXXXA9', 'state_code': 'ZS', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00033', 'created_date': '2026-10-10', 'full_name': 'Camila Campos Vargas', 'email': 'camila.campos.2026101033@example.com', 'phone': '+525922689495', 'rfc': 'BADRFC', 'curp': 'CXVC860906HNEXXX59', 'state_code': 'NE', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00034', 'created_date': '2026-10-10', 'full_name': 'Renata Ramirez Vargas', 'email': 'renata.ramirez.2026101034@example.com', 'phone': '+525240728195', 'rfc': 'BADRFC', 'curp': 'RXVR871007MASXXXP6', 'state_code': 'AS', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00035', 'created_date': '2026-10-10', 'full_name': 'Ivan Castillo Martinez', 'email': 'ivan.castillo.2026101035@example.com', 'phone': '+522988040933', 'rfc': 'BADRFC', 'curp': 'CXMI881108HBCXXXB9', 'state_code': 'BC', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00036', 'created_date': '2026-10-10', 'full_name': 'Irene Silva Ramirez', 'email': 'irene.silva.2026101036@example.com', 'phone': '+524275942673', 'rfc': 'BADRFC', 'curp': 'SXRI891209MBSXXXT5', 'state_code': 'BS', 'segment': 'residential', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-10 · customers · `customers_segment_drift`

- Severity: medium
- Metric: psi = 0.6301 (threshold <= 0.2)
- Offending rows: 86 of 86
- PSI 0.6301 exceeds 0.20 for segment against the first 14 business dates

Sample:

```
{'category': 'commercial', 'actual_rows': 20, 'actual_share': 0.23255813953488372, 'reference_rows': 336, 'reference_share': 0.3}
{'category': 'residential', 'actual_rows': 62, 'actual_share': 0.7209302325581395, 'reference_rows': 784, 'reference_share': 0.7}
{'category': 'unknown', 'actual_rows': 4, 'actual_share': 0.046511627906976744, 'reference_rows': 0, 'reference_share': 0.0}
```

### 2026-10-10 · customers · `customers_segment_values`

- Severity: low
- Metric: rejected_rows = 4 (threshold == 0)
- Offending rows: 4 of 86
- 4 of 86 rows are outside accepted values (residential, commercial)

Sample:

```
{'customer_id': 'CUS-20261010-00070', 'created_date': '2026-10-10', 'full_name': 'Paula Lopez Aguilar', 'email': 'paula.lopez.2026101070@example.com', 'phone': '+522824130160', 'rfc': 'LXAP931016CNS', 'curp': 'LXAP931016MCCXXX93', 'state_code': 'CC', 'segment': 'unknown', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00071', 'created_date': '2026-10-10', 'full_name': 'Irene Medina Navarro', 'email': 'irene.medina.2026101071@example.com', 'phone': '+525417733430', 'rfc': 'MXNI941117QQC', 'curp': 'MXNI941117HCLXXXM5', 'state_code': 'CL', 'segment': 'unknown', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00072', 'created_date': '2026-10-10', 'full_name': 'Rosa Rojas Guerrero', 'email': 'rosa.rojas.2026101072@example.com', 'phone': '+524160639231', 'rfc': 'RXGR9512183H9', 'curp': 'RXGR951218MCMXXXJ1', 'state_code': 'CM', 'segment': 'unknown', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
{'customer_id': 'CUS-20261010-00073', 'created_date': '2026-10-10', 'full_name': 'Elena Paredes Morales', 'email': 'elena.paredes.2026101073@example.com', 'phone': '+522238836970', 'rfc': 'PXME96011937H', 'curp': 'PXME960119HCSXXXF0', 'state_code': 'CS', 'segment': 'unknown', 'status': 'active', 'loaded_at': '2026-10-11 05:00:00'}
```

### 2026-10-11 · daily_route_kpis · `kpis_golden_reconciliation`

- Severity: critical
- Metric: metrics_breached = 2 (threshold == 0)
- Offending rows: 2 of 2
- shipment_count actual 1015 expected 1000 (abs diff 15, tolerance 0.0); weight_g_sum actual 1509785.00 expected 1502300.00 (abs diff 7485.00, tolerance 0.01)

Sample:

```
{'metric': 'shipment_count', 'actual': '1015', 'expected': '1000', 'breached': True}
{'metric': 'weight_g_sum', 'actual': '1509785.00', 'expected': '1502300.00', 'breached': True}
```

### 2026-10-11 · shipments · `shipments_customer_fk`

- Severity: critical
- Metric: orphan_rows = 15 (threshold == 0)
- Offending rows: 15 of 1015
- 15 of 1015 rows reference a missing customers.customer_id

Sample:

```
{'shipment_id': 'SHP-20261011-X-0000', 'business_date': '2026-10-11', 'customer_id': 'CUS-MISSING-0000', 'hub_id': 'HUB-00001', 'courier_name': 'Sol', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 12:00:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-X-0001', 'business_date': '2026-10-11', 'customer_id': 'CUS-MISSING-0001', 'hub_id': 'HUB-00001', 'courier_name': 'Bruma', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 12:01:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-X-0002', 'business_date': '2026-10-11', 'customer_id': 'CUS-MISSING-0002', 'hub_id': 'HUB-00001', 'courier_name': 'Nube', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 12:02:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-X-0003', 'business_date': '2026-10-11', 'customer_id': 'CUS-MISSING-0003', 'hub_id': 'HUB-00001', 'courier_name': 'Cedra', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 12:03:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-X-0004', 'business_date': '2026-10-11', 'customer_id': 'CUS-MISSING-0004', 'hub_id': 'HUB-00001', 'courier_name': 'Duna', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 12:04:00', 'loaded_at': '2026-10-12 05:00:00'}
```

### 2026-10-11 · shipments · `shipments_hub_fk`

- Severity: critical
- Metric: orphan_rows = 7 (threshold == 0)
- Offending rows: 7 of 1015
- 7 of 1015 rows reference a missing hubs.hub_id

Sample:

```
{'shipment_id': 'SHP-20261011-0-0000', 'business_date': '2026-10-11', 'customer_id': 'CUS-20260901-00001', 'hub_id': 'HUB-MISSING', 'courier_name': 'Sol', 'weight_g': '250.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 08:00:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-0-0001', 'business_date': '2026-10-11', 'customer_id': 'CUS-20260901-00002', 'hub_id': 'HUB-MISSING', 'courier_name': 'Bruma', 'weight_g': '1200.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-11 09:03:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-0-0002', 'business_date': '2026-10-11', 'customer_id': 'CUS-20260901-00003', 'hub_id': 'HUB-MISSING', 'courier_name': 'Nube', 'weight_g': '1200.00', 'country_code': 'MX', 'channel': 'branch', 'status': 'delivered', 'shipped_at': '2026-10-11 10:06:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-0-0003', 'business_date': '2026-10-11', 'customer_id': 'CUS-20260901-00004', 'hub_id': 'HUB-MISSING', 'courier_name': 'Cedra', 'weight_g': '250.00', 'country_code': 'MX', 'channel': 'locker', 'status': 'in_transit', 'shipped_at': '2026-10-11 11:09:00', 'loaded_at': '2026-10-12 05:00:00'}
{'shipment_id': 'SHP-20261011-0-0004', 'business_date': '2026-10-11', 'customer_id': 'CUS-20260901-00005', 'hub_id': 'HUB-MISSING', 'courier_name': 'Duna', 'weight_g': '1200.00', 'country_code': 'MX', 'channel': 'locker', 'status': 'delivered', 'shipped_at': '2026-10-11 12:12:00', 'loaded_at': '2026-10-12 05:00:00'}
```

### 2026-10-11 · tracking_scans · `scans_customer_fk`

- Severity: critical
- Metric: orphan_rows = 5 (threshold == 0)
- Offending rows: 5 of 85
- 5 of 85 rows reference a missing customers.customer_id

Sample:

```
{'scan_id': 'SCN-ORPHAN-20261011-00', 'customer_id': 'CUS-MISSING-SCN-0000', 'business_date': '2026-10-11', 'device_type': 'handheld', 'barcode': 'ORPHANPKG0000', 'scan_event': 'pickup', 'dwell_minutes': 10, 'scanned_at': '2026-10-11 11:00:00', 'relayed_at': '2026-10-11 12:00:00', 'loaded_at': '2026-10-12 05:00:00'}
{'scan_id': 'SCN-ORPHAN-20261011-01', 'customer_id': 'CUS-MISSING-SCN-0001', 'business_date': '2026-10-11', 'device_type': 'handheld', 'barcode': 'ORPHANPKG0001', 'scan_event': 'pickup', 'dwell_minutes': 10, 'scanned_at': '2026-10-11 11:01:00', 'relayed_at': '2026-10-11 12:01:00', 'loaded_at': '2026-10-12 05:00:00'}
{'scan_id': 'SCN-ORPHAN-20261011-02', 'customer_id': 'CUS-MISSING-SCN-0002', 'business_date': '2026-10-11', 'device_type': 'handheld', 'barcode': 'ORPHANPKG0002', 'scan_event': 'pickup', 'dwell_minutes': 10, 'scanned_at': '2026-10-11 11:02:00', 'relayed_at': '2026-10-11 12:02:00', 'loaded_at': '2026-10-12 05:00:00'}
{'scan_id': 'SCN-ORPHAN-20261011-03', 'customer_id': 'CUS-MISSING-SCN-0003', 'business_date': '2026-10-11', 'device_type': 'handheld', 'barcode': 'ORPHANPKG0003', 'scan_event': 'pickup', 'dwell_minutes': 10, 'scanned_at': '2026-10-11 11:03:00', 'relayed_at': '2026-10-11 12:03:00', 'loaded_at': '2026-10-12 05:00:00'}
{'scan_id': 'SCN-ORPHAN-20261011-04', 'customer_id': 'CUS-MISSING-SCN-0004', 'business_date': '2026-10-11', 'device_type': 'handheld', 'barcode': 'ORPHANPKG0004', 'scan_event': 'pickup', 'dwell_minutes': 10, 'scanned_at': '2026-10-11 11:04:00', 'relayed_at': '2026-10-11 12:04:00', 'loaded_at': '2026-10-12 05:00:00'}
```

### 2026-10-12 · daily_route_kpis · `kpis_golden_reconciliation`

- Severity: critical
- Metric: metrics_breached = 2 (threshold == 0)
- Offending rows: 2 of 2
- shipment_count actual 200 expected 1000 (abs diff 800, tolerance 0.0); weight_g_sum actual 300460.00 expected 1502300.00 (abs diff 1201840.00, tolerance 0.01)

Sample:

```
{'metric': 'shipment_count', 'actual': '200', 'expected': '1000', 'breached': True}
{'metric': 'weight_g_sum', 'actual': '300460.00', 'expected': '1502300.00', 'breached': True}
```

### 2026-10-12 · shipments · `shipments_volume_anomaly`

- Severity: high
- Metric: volume_deviation = 0.8 (threshold <= 0.35)
- Offending rows: 800 of 200
- row count 200 deviates 80.00% from the trailing 14-day median 1000 (limit 35.00%)

Sample:

```
{'shipment_id': 'SHP-20261012-0-0000', 'business_date': '2026-10-12', 'customer_id': 'CUS-20260901-00001', 'hub_id': 'HUB-00001', 'courier_name': 'Sol', 'weight_g': '499.00', 'country_code': 'MX', 'channel': 'branch', 'status': 'delivered', 'shipped_at': '2026-10-12 08:00:00', 'loaded_at': '2026-10-13 05:00:00'}
{'shipment_id': 'SHP-20261012-0-0001', 'business_date': '2026-10-12', 'customer_id': 'CUS-20260901-00002', 'hub_id': 'HUB-00002', 'courier_name': 'Bruma', 'weight_g': '250.00', 'country_code': 'MX', 'channel': 'counter', 'status': 'delivered', 'shipped_at': '2026-10-12 09:03:00', 'loaded_at': '2026-10-13 05:00:00'}
{'shipment_id': 'SHP-20261012-0-0002', 'business_date': '2026-10-12', 'customer_id': 'CUS-20260901-00003', 'hub_id': 'HUB-00003', 'courier_name': 'Nube', 'weight_g': '250.00', 'country_code': 'MX', 'channel': 'branch', 'status': 'delivered', 'shipped_at': '2026-10-12 10:06:00', 'loaded_at': '2026-10-13 05:00:00'}
{'shipment_id': 'SHP-20261012-0-0003', 'business_date': '2026-10-12', 'customer_id': 'CUS-20260901-00004', 'hub_id': 'HUB-00004', 'courier_name': 'Cedra', 'weight_g': '3500.00', 'country_code': 'MX', 'channel': 'home', 'status': 'delivered', 'shipped_at': '2026-10-12 11:09:00', 'loaded_at': '2026-10-13 05:00:00'}
{'shipment_id': 'SHP-20261012-0-0004', 'business_date': '2026-10-12', 'customer_id': 'CUS-20260901-00005', 'hub_id': 'HUB-00005', 'courier_name': 'Duna', 'weight_g': '250.00', 'country_code': 'MX', 'channel': 'locker', 'status': 'delivered', 'shipped_at': '2026-10-12 12:12:00', 'loaded_at': '2026-10-13 05:00:00'}
```

### 2026-10-13 · shipments · `shipments_channel_drift`

- Severity: medium
- Metric: psi = 3.2783 (threshold <= 0.2)
- Offending rows: 1000 of 1000
- PSI 3.2783 exceeds 0.20 for channel against the first 14 business dates

Sample:

```
{'category': 'branch', 'actual_rows': 50, 'actual_share': 0.05, 'reference_rows': 3500, 'reference_share': 0.25}
{'category': 'counter', 'actual_rows': 800, 'actual_share': 0.8, 'reference_rows': 700, 'reference_share': 0.05}
{'category': 'home', 'actual_rows': 100, 'actual_share': 0.1, 'reference_rows': 7700, 'reference_share': 0.55}
{'category': 'locker', 'actual_rows': 50, 'actual_share': 0.05, 'reference_rows': 2100, 'reference_share': 0.15}
```

### 2026-10-15 · tracking_scans · `scans_freshness`

- Severity: critical
- Metric: lateness_hours = 12 (threshold <= 0)
- Offending rows: 80 of 80
- arrived 12.00 hours after the deadline (loaded_at 2026-10-16 20:00, deadline 2026-10-16 08:00)

Sample:

```
{'scan_id': 'SCN-20261015-00001', 'customer_id': 'CUS-20261015-00001', 'business_date': '2026-10-15', 'device_type': 'handheld', 'barcode': 'PKG2026101500001', 'scan_event': 'pickup', 'dwell_minutes': 0, 'scanned_at': '2026-10-15 10:00:00', 'relayed_at': '2026-10-15 14:00:00', 'loaded_at': '2026-10-16 20:00:00'}
{'scan_id': 'SCN-20261015-00002', 'customer_id': 'CUS-20261015-00002', 'business_date': '2026-10-15', 'device_type': 'handheld', 'barcode': 'PKG2026101500002', 'scan_event': 'pickup', 'dwell_minutes': 17, 'scanned_at': '2026-10-15 10:01:00', 'relayed_at': '2026-10-15 14:01:00', 'loaded_at': '2026-10-16 20:00:00'}
{'scan_id': 'SCN-20261015-00003', 'customer_id': 'CUS-20261015-00003', 'business_date': '2026-10-15', 'device_type': 'handheld', 'barcode': 'PKG2026101500003', 'scan_event': 'pickup', 'dwell_minutes': 34, 'scanned_at': '2026-10-15 10:02:00', 'relayed_at': '2026-10-15 14:02:00', 'loaded_at': '2026-10-16 20:00:00'}
{'scan_id': 'SCN-20261015-00004', 'customer_id': 'CUS-20261015-00004', 'business_date': '2026-10-15', 'device_type': 'handheld', 'barcode': 'PKG2026101500004', 'scan_event': 'pickup', 'dwell_minutes': 51, 'scanned_at': '2026-10-15 10:03:00', 'relayed_at': '2026-10-15 14:03:00', 'loaded_at': '2026-10-16 20:00:00'}
{'scan_id': 'SCN-20261015-00005', 'customer_id': 'CUS-20261015-00005', 'business_date': '2026-10-15', 'device_type': 'handheld', 'barcode': 'PKG2026101500005', 'scan_event': 'pickup', 'dwell_minutes': 68, 'scanned_at': '2026-10-15 10:04:00', 'relayed_at': '2026-10-15 14:04:00', 'loaded_at': '2026-10-16 20:00:00'}
```
