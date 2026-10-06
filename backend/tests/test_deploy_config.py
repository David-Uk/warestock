"""Tests for the deployment configuration (observability stack + Vercel).

The dashboard JSON itself is covered by ``test_metrics.py``; these tests make
sure the scrape config, Grafana provisioning and the compose wiring that make
that dashboard usable all stay consistent with each other. The Vercel class
guards the Python runtime wiring: entrypoint, bundle trimming and the upload
exclusions that keep a 750 MB virtualenv out of the deployment.
"""

from __future__ import annotations

import fnmatch
import json
import tomllib
from collections.abc import Iterator
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
PROMETHEUS_CONFIG = REPO_ROOT / "deploy" / "prometheus" / "prometheus.yml"
DATASOURCE_CONFIG = (
    REPO_ROOT / "deploy" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
)
DASHBOARD_PROVIDER = (
    REPO_ROOT / "deploy" / "grafana" / "provisioning" / "dashboards" / "warestock.yml"
)
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
DASHBOARD_JSON = REPO_ROOT / "backend" / "grafana" / "warestock-backend-dashboard.json"


def _load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} did not parse to a mapping"
    return data


class TestPrometheusScrapeConfig:
    def test_scrapes_the_backend_metrics_endpoint(self):
        config = _load(PROMETHEUS_CONFIG)

        jobs = config["scrape_configs"]
        backend = next(job for job in jobs if job["job_name"] == "warestock-backend")

        assert backend["metrics_path"] == "/metrics"
        assert backend["static_configs"][0]["targets"] == ["backend:8000"]

    def test_scrape_interval_is_sub_15s(self):
        config = _load(PROMETHEUS_CONFIG)
        backend = next(
            job for job in config["scrape_configs"] if job["job_name"] == "warestock-backend"
        )

        assert backend["scrape_interval"] == "10s"


class TestGrafanaProvisioning:
    def test_prometheus_datasource_points_at_the_scrape_service(self):
        datasources = _load(DATASOURCE_CONFIG)["datasources"]
        prometheus = next(ds for ds in datasources if ds["type"] == "prometheus")

        assert prometheus["url"] == "http://prometheus:9090"
        assert prometheus["isDefault"] is True

    def test_dashboard_provider_reads_the_committed_template(self):
        provider = _load(DASHBOARD_PROVIDER)["providers"][0]

        assert provider["type"] == "file"
        assert provider["options"]["path"] == "/var/lib/grafana/dashboards"
        assert DASHBOARD_JSON.is_file()

    def test_dashboard_template_exists_and_is_provisionable(self):
        assert DASHBOARD_JSON.is_file()
        assert DASHBOARD_JSON.stat().st_size > 0


class TestComposeStack:
    def test_prometheus_and_grafana_services_are_defined(self):
        services = _load(COMPOSE_FILE)["services"]

        assert "prometheus" in services
        assert "grafana" in services
        assert services["prometheus"]["depends_on"] == ["backend"]
        assert services["grafana"]["depends_on"] == ["prometheus"]

    def test_config_files_are_mounted_read_only(self):
        services = _load(COMPOSE_FILE)["services"]

        assert (
            "./deploy/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro"
            in services["prometheus"]["volumes"]
        )
        assert "./backend/grafana:/var/lib/grafana/dashboards:ro" in services["grafana"]["volumes"]
        assert (
            "./deploy/grafana/provisioning:/etc/grafana/provisioning:ro"
            in services["grafana"]["volumes"]
        )

    def test_monitoring_uis_do_not_collide_with_existing_ports(self):
        services = _load(COMPOSE_FILE)["services"]
        used = {
            port
            for name in ("db", "backend", "web", "prometheus", "grafana")
            for port in services[name].get("ports", [])
        }

        assert services["prometheus"]["ports"] == ["9090:9090"]
        assert services["grafana"]["ports"] == ["3001:3000"]
        assert len(used) == len({split.split(":")[0] for split in used})

    def test_backend_service_is_reachable_for_scraping(self):
        services = _load(COMPOSE_FILE)["services"]

        assert services["backend"]["ports"] == ["8000:8000"]


VERCEL_JSON = BACKEND_ROOT / "vercel.json"
VERCELIGNORE = BACKEND_ROOT / ".vercelignore"
PYTHON_VERSION_FILE = BACKEND_ROOT / ".python-version"
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# Files the running application opens itself: migrations at startup, the CA
# bundle for the managed database, the ASGI app and its static assets.
RUNTIME_FILES = (
    "app/main.py",
    "app/static/index.html",
    "alembic/env.py",
    "alembic/versions/001_initial_schema.py",
    "alembic.ini",
    "cert/warestock.pem",
    "requirements.txt",
    "pyproject.toml",
)


def _vercelignore_entries() -> set[str]:
    return {
        line.strip()
        for line in VERCELIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _find_values(node: object, key: str) -> Iterator[object]:
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                yield value
            yield from _find_values(value, key)
    elif isinstance(node, list):
        for item in node:
            yield from _find_values(item, key)


class TestVercelDeployment:
    def _vercel_json(self) -> dict:
        return json.loads(VERCEL_JSON.read_text(encoding="utf-8"))

    def _exclude_globs(self) -> list[str]:
        pattern = self._vercel_json()["functions"]["app/main.py"]["excludeFiles"]
        return [glob.strip() for glob in pattern.strip("{}").split(",")]

    def test_pyproject_declares_the_entrypoint(self):
        pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

        assert pyproject["tool"]["vercel"]["entrypoint"] == "app.main:app"

    def test_functions_key_matches_the_entrypoint_module(self):
        pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        module = pyproject["tool"]["vercel"]["entrypoint"].split(":")[0]
        expected_key = f"{module.replace('.', '/')}.py"
        functions = self._vercel_json()["functions"]

        assert expected_key in functions
        assert (BACKEND_ROOT / expected_key).is_file()

    def test_function_timeout_is_within_the_schema_limits(self):
        max_duration = self._vercel_json()["functions"]["app/main.py"]["maxDuration"]

        assert 1 <= max_duration <= 1800

    def test_exclude_pattern_fits_the_schema_limit(self):
        # vercel.json's schema caps excludeFiles at 256 characters.
        pattern = self._vercel_json()["functions"]["app/main.py"]["excludeFiles"]

        assert len(pattern) <= 256

    def test_exclude_pattern_keeps_the_files_the_app_reads_at_runtime(self):
        globs = self._exclude_globs()

        for path in RUNTIME_FILES:
            assert not any(fnmatch.fnmatch(path, glob) for glob in globs), (
                f"{path} would be stripped from the function bundle"
            )

    def test_exclude_pattern_actually_matches_the_dead_weight(self):
        globs = self._exclude_globs()

        for path in (
            "tests/test_main.py",
            ".venv/lib/python3.13/site-packages/fastapi/__init__.py",
            "demo_recordings/browser_demo.mp4",
            "app/__pycache__/main.cpython-313.pyc",
            ".env",
        ):
            assert any(fnmatch.fnmatch(path, glob) for glob in globs), (
                f"{path} would still be bundled"
            )

    def test_vercelignore_hides_venvs_secrets_and_media(self):
        assert {
            ".venv/",
            "env/",
            ".env",
            ".env.*",
            "tests/",
            "*.mp4",
            "*.webm",
            ".mypy_cache/",
            ".pytest_cache/",
            "demo_recordings/",
            ".vercel/",
        } <= _vercelignore_entries()

    def test_vercelignore_keeps_what_the_runtime_needs(self):
        entries = _vercelignore_entries()

        for needed in ("app/", "alembic/", "alembic.ini", "cert/", "requirements.txt"):
            assert needed not in entries

    def test_python_version_matches_ci(self):
        configured = PYTHON_VERSION_FILE.read_text(encoding="utf-8").strip()
        workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        ci_versions = set(_find_values(workflow, "python-version"))

        assert ci_versions == {configured}
