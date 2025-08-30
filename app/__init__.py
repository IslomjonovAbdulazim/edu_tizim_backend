from __future__ import annotations

# Package metadata pulled from settings when available
try:
    from .core.config import settings
    __version__ = settings.VERSION
    PROJECT_NAME = settings.PROJECT_NAME
except Exception:  # graceful during early scaffolding / tests
    __version__ = "0.0.0"
    PROJECT_NAME = "App"

# Re-export API helpers/routers for convenience
try:
    from .api import include_apis, api_v1, api_v1_router
except Exception:
    # Keep imports lazy-safe if API layer isn't present yet
    def include_apis(*_args, **_kwargs):  # type: ignore
        raise RuntimeError("API routers are not available yet.")
    api_v1 = None        # type: ignore
    api_v1_router = None # type: ignore

__all__ = ["__version__", "PROJECT_NAME", "include_apis", "api_v1", "api_v1_router"]
