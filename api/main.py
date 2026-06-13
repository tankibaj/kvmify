"""KVMify FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import networks, pools

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KVMify",
    version="0.1.0",
    description="Self-service web UI for KVM virtual machine management.",
    # /docs and /redoc are enabled by default
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Liveness probe — always returns 200 when the process is up."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Router registration — add new routers here as new phases are implemented
# ---------------------------------------------------------------------------

app.include_router(networks.router, prefix="/networks", tags=["networks"])
app.include_router(pools.router, prefix="/pools", tags=["pools"])
