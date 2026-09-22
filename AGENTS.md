# AGENTS.md

Astro CLI (Astronomer) Apache Airflow project on Astro Runtime 3.3-7 (Airflow 3.3.1, Python 3.14). All local development runs through the Astro CLI + Docker on top of the base image in `Dockerfile`. Do not try to run Airflow from the host via `uv`/`pip`.

## Commands
- `astro dev start` — bring up local Airflow (webserver at localhost:8080); `astro dev stop` / `astro dev restart` / `astro dev logs --follow`
- `astro dev parse` — DAG validation. Runs `.astro/test_dag_integrity_default.py`, which monkeypatches Connections/Variables/getenv so parse passes even without real GCP creds.
- `astro dev pytest` — runs the pytest suite under `tests/` in the local Airflow environment (there is no top-level `astro test` command in this CLI).

## Tests
- `tests/dags/test_dag_example.py` asserts every DAG (1) imports with no errors, (2) has a `tags` list, (3) sets `default_args["retries"] >= 2`.
- No pytest.ini/CI/pre-commit exist; the Astro CLI is the only test/verify path.

## DAG architecture
- Only real DAG: `dags/retail.py`. Flow: upload `include/dataset/online_retail.csv` → GCS bucket `retail-project-dbt` (path `raw/online_retail.csv`) → create BigQuery dataset `retail` → `GCSToBigQueryOperator` loads into `retail-dbt-airflow.retail.raw_invoices`. All tasks use `gcp_conn_id='gcp'`.
- Inside the container, project paths are `/usr/local/airflow/...` (e.g. `src='/usr/local/airflow/include/dataset/online_retail.csv'`), not host paths.
- The `gcp` connection is configured nowhere in the repo (`airflow_settings.yaml` is an empty template). DAG runs need it created in the Airflow UI, in `airflow_settings.yaml`, or via env var — `astro dev parse` won't catch a missing connection.
- Do NOT use `astro-sdk-python` (`aql.load_file`, astro XCom backend) here: its latest release (1.8.1) predates Airflow 3 and declares `apache-airflow>=2.7` (README says >=2.1.0) — Airflow 3.3 satisfies that, so the version constraint is NOT the blocker. The real blocker is its `pandas<2.2.0` pin, which conflicts with this runtime's google provider on Python 3.13/3.14 (`pandas>=2.2.3` / `>=2.3.3`), so `uv` image builds fail; only the `-python-3.12` base image variant would resolve it. The gcs_to_raw task was deliberately rewritten with `GCSToBigQueryOperator` from the google provider instead.

## Dependencies
- `pyproject.toml` + `uv.lock` drive local Python (uv) only. The Docker build installs ONLY `requirements.txt` — packages there must be uncommented/pinned explicitly or they won't exist in the container.
- Astro Runtime 3.3-7 ships google providers but NOT `astro-sdk-python`. If an astro XCom backend or `astro` imports are ever re-enabled, the package must be installable in the image or every Airflow process crash-loops (`No module named 'astro'`).
- Docker build context excludes `airflow_settings.yaml` and `.env` (see `.dockerignore`).

## Secrets / gotchas
- `include/gcp/service_account.json` is a real GCP service-account private key already committed. Never add new credentials to the repo; reuse existing files, `.env`, or env-config.
- `.env` (gitignored) is minimal (`AIRFLOW__CORE__TEST_CONNECTION=Enabled`) and is passed into the container by `astro dev start`. The astro XCom backend lines were removed when astro-sdk was dropped.
- `dags/exampledag.py` is deleted in the working tree (uncommitted); don't recreate it, and `dags/.airflowignore` is intentionally empty.