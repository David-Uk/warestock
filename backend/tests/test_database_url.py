"""DATABASE_URL normalisation and the managed-Postgres CA bundle.

The production URL handed to the deployment uses the legacy ``postgres://``
scheme and ``sslmode=require``. Both are adjusted while ``Settings`` is
constructed, so the async engine, Alembic's ``env.py`` and the test fixtures
all open the same driver-ready, certificate-verified connection.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
from cryptography import x509
from pydantic import ValidationError

from app.config import Settings, normalise_database_url, resolve_postgres_ca_cert
from app.db.session import pool_kwargs

BACKEND_ROOT = Path(__file__).resolve().parents[1]
CA_CERT = BACKEND_ROOT / "cert" / "warestock.pem"
PROD_URL = "postgres://user:secret@db.example.internal:5432/app?sslmode=require"
LOCAL_URL = "postgresql+psycopg://postgres:Database%4091@127.0.0.1:5432/warestock"


def _query(url: str) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))


class TestSchemeNormalisation:
    def test_legacy_scheme_gains_the_async_driver(self):
        url = normalise_database_url("postgres://u:p@host:5432/db", None, True)

        assert url.startswith("postgresql+psycopg://")

    def test_url_already_on_the_async_driver_is_kept(self):
        assert normalise_database_url(LOCAL_URL, None, True) == LOCAL_URL

    def test_authority_is_rewritten_verbatim(self):
        normalised = normalise_database_url(PROD_URL, CA_CERT, True)

        assert urlsplit(normalised).netloc == "user:secret@db.example.internal:5432"


class TestTlsVerification:
    def test_require_is_upgraded_when_a_ca_is_available(self):
        normalised = normalise_database_url(PROD_URL, CA_CERT, True)
        query = _query(normalised)

        assert query["sslmode"] == "verify-full"
        assert query["sslrootcert"] == CA_CERT.as_posix()

    def test_require_survives_when_verification_is_disabled(self):
        query = _query(normalise_database_url(PROD_URL, CA_CERT, False))

        assert query["sslmode"] == "require"
        assert "sslrootcert" not in query

    def test_local_url_with_no_sslmode_is_untouched(self):
        # Local development talks to a plain database with no sslmode at all;
        # auto-attaching a CA there would only create a way to fail.
        assert normalise_database_url(LOCAL_URL, CA_CERT, True) == LOCAL_URL

    def test_existing_sslrootcert_is_not_overwritten(self):
        url = (
            "postgresql+psycopg://u:p@h:5432/db?sslmode=verify-full&sslrootcert=%2Ftmp%2Fother.pem"
        )

        assert normalise_database_url(url, CA_CERT, True) == url

    def test_verification_without_a_ca_is_left_alone(self):
        url = "postgresql+psycopg://u:p@h:5432/db?sslmode=verify-full"

        assert normalise_database_url(url, None, True) == url


class TestCaBundle:
    def test_bundled_ca_is_auto_detected(self):
        assert resolve_postgres_ca_cert("") == CA_CERT

    def test_explicit_path_is_resolved_against_the_backend_root(self):
        assert resolve_postgres_ca_cert("cert/warestock.pem") == CA_CERT

    def test_explicit_path_that_does_not_exist_fails_closed(self):
        with pytest.raises(ValueError, match="POSTGRES_CA_CERT_PATH"):
            resolve_postgres_ca_cert("cert/missing.pem")

    def test_bundled_ca_is_a_valid_x509_certificate_authority(self):
        certificate = x509.load_pem_x509_certificate(CA_CERT.read_bytes())

        assert certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
        assert certificate.not_valid_before_utc < certificate.not_valid_after_utc


class TestSettingsWiring:
    def test_managed_database_url_is_upgraded_in_place(self):
        settings = Settings(_env_file=None, DATABASE_URL=PROD_URL)
        query = _query(settings.DATABASE_URL)

        assert urlsplit(settings.DATABASE_URL).scheme == "postgresql+psycopg"
        assert query["sslmode"] == "verify-full"
        assert query["sslrootcert"] == CA_CERT.as_posix()

    def test_local_database_url_is_passed_through_unchanged(self):
        settings = Settings(_env_file=None, DATABASE_URL=LOCAL_URL)

        assert settings.DATABASE_URL == LOCAL_URL

    def test_missing_ca_path_refuses_to_build_settings(self):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, POSTGRES_CA_CERT_PATH="cert/missing.pem")


class TestServerlessPool:
    def test_pool_is_narrow_on_vercel(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("VERCEL", "1")

        assert pool_kwargs() == {"pool_size": 1, "max_overflow": 0}

    def test_pool_stays_wide_everywhere_else(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("VERCEL", raising=False)

        assert pool_kwargs() == {"pool_size": 10, "max_overflow": 20}
