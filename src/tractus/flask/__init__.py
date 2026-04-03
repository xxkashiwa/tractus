"""Flask web layer (HTTP API).

This package contains the Flask app factory and HTTP route handlers.
"""

from .app import create_app

__all__ = [
    "create_app",
]
