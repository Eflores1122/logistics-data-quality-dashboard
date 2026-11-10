.PHONY: install generate run evaluate report dashboard test lint

install:
	python -m pip install -e ".[dev,dashboard]"

generate:
	rutanorte-dq generate

run: generate
	rutanorte-dq run

evaluate: run
	rutanorte-dq evaluate

report: run
	rutanorte-dq report --format markdown --output reports/dq_report.md
	rutanorte-dq report --format html --output reports/dq_report.html

dashboard: run
	streamlit run dashboard/app.py

site-data:
	python scripts/export_browser_warehouse.py

site:
	npm run build

test:
	pytest

lint:
	ruff check .
	ruff format --check .
