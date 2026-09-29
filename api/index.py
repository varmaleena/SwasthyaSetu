"""Vercel ASGI entrypoint. The application and credentials stay server-side."""
from services.api.main import app

__all__ = ["app"]
