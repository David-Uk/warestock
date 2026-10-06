"""Settings must boot in any environment (no unresolved config issues)."""

from __future__ import annotations

from app.config import Settings


class TestSettingsResilience:
    def test_unknown_init_values_are_ignored(self):
        settings = Settings(_env_file=None, REDIS_API_KEY="not-a-modelled-field")

        assert settings.APP_ENV
        assert not hasattr(settings, "redis_api_key")

    def test_declared_defaults_still_apply(self):
        settings = Settings(_env_file=None)

        assert settings.ALGORITHM == "HS256"
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_typed_fields_reject_bad_values(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(_env_file=None, REFRESH_TOKEN_EXPIRE_DAYS="not-an-int")
