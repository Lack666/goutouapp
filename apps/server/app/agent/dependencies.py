"""Dependency injection shape for a later runtime; no concrete service is created."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.agent.state import RelationshipProfile, UserProfile
from app.llm.provider import LLMProvider


class ProfileReader(Protocol):
    async def load_user_profile(self, user_id: UUID) -> UserProfile | None: ...

    async def load_relationship_profile(
        self, user_id: UUID, relationship_id: UUID
    ) -> RelationshipProfile | None: ...


@dataclass(frozen=True)
class RuntimeDependencies:
    llm_provider: LLMProvider
    profile_reader: ProfileReader | None = None
