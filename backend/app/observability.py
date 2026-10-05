"""Sentry integration: error tracking, performance monitoring, user context.

Initialisation is driven by the ``SENTRY_DSN`` environment variable; with no
DSN configured (the default in development and CI) every helper here is a
no-op and the SDK stays disabled, so tests never send events anywhere.
"""

import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import Settings
from app.models.user import User

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> bool:
    """Initialise the Sentry SDK when a DSN is configured.

    Returns True when Sentry is enabled. The FastAPI integration captures
    errors with request context; the SQLAlchemy integration emits database
    query spans sampled by ``SENTRY_TRACES_SAMPLE_RATE``.
    """
    if not settings.SENTRY_DSN:
        logger.info("Sentry disabled: SENTRY_DSN is not configured")
        return False

    environment = settings.SENTRY_ENVIRONMENT or settings.APP_ENV
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=environment,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
    )
    logger.info("Sentry initialised (environment=%s)", environment)
    return True


def set_user_context(user: User | None) -> None:
    """Attach the authenticated user to the current Sentry scope.

    Called from the auth dependencies so every event captured while handling
    an authenticated request identifies the acting user, their roles and
    tenant organisation.
    """
    if user is None:
        return
    sentry_sdk.set_user(
        {
            "id": str(user.id),
            "email": user.email,
            "tenant_role": user.tenant_role.value if user.tenant_role else None,
            "platform_role": user.platform_role.value if user.platform_role else None,
            "organisation_id": str(user.organisation_id) if user.organisation_id else None,
        }
    )


def capture_background_error(error: BaseException, **context: object) -> None:
    """Capture a background-task failure with task context attached.

    Background tasks run outside any HTTP request scope, so the FastAPI
    integration cannot decorate the event — extras are set explicitly.
    """
    with sentry_sdk.configure_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
    sentry_sdk.capture_exception(error)
