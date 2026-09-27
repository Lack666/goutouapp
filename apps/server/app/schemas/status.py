"""Responses for the foundation-only status routes."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class StatusResponse(BaseModel):
    service: Literal["goutoujunshi-server"] = "goutoujunshi-server"
    status: Literal["running"] = "running"
    environment: str
