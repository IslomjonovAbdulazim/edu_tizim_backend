from __future__ import annotations
from fastapi import FastAPI

# Re-export v1 routers for convenience
from .v1 import api_v1 as api_v1
from .v1 import api_router as api_v1_router  # compat alias

# Map of version -> router (easy to extend later)
VERSIONS = {
    "v1": api_v1,
}

def include_apis(app: FastAPI, base_prefix: str = "/api") -> None:
    """
    Mount all API versions under a common base prefix.
    Example:
        include_apis(app)  # mounts /api/v1
    """
    app.include_router(api_v1, prefix=f"{base_prefix}/v1")

__all__ = ["api_v1", "api_v1_router", "include_apis", "VERSIONS"]
