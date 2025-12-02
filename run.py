"""Simple script to run TokenRouter."""
import sys
import logging

import uvicorn

# Configure logging format with timestamps
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": DATE_FORMAT,
        },
        "access": {
            # Use standard format - uvicorn passes access info as the message
            "format": "%(asctime)s - %(levelname)s - %(message)s",
            "datefmt": DATE_FORMAT,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_config=LOGGING_CONFIG
        )
    except KeyboardInterrupt:
        print("\n\n👋 TokenRouter stopped")
    except Exception as e:
        print(f"\n❌ Error starting TokenRouter: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")

