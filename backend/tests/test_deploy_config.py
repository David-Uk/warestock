"""Tests for the Prometheus/Grafana deployment stack (issue #14).

The dashboard JSON itself is covered by ``test_metrics.py``; these tests make
sure the scrape config, Grafana provisioning and the compose wiring that make
that dashboard usable all stay consistent with each other.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
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
