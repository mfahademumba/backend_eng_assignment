from __future__ import annotations

import logging.config
from typing import Any

from config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure application logging with a consistent console format."""
    log_level = settings.log_level.upper()

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": ("%(asctime)s %(levelname)s [%(name)s] %(message)s"),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            "app": {
                "level": log_level,
                "propagate": True,
            },
            "main": {
                "level": log_level,
                "propagate": True,
            },
            "uvicorn": {
                "level": log_level,
                "propagate": True,
            },
            "uvicorn.error": {
                "level": log_level,
                "propagate": True,
            },
            "uvicorn.access": {
                "level": log_level,
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(logging_config)
