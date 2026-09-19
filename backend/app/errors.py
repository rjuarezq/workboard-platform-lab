from dataclasses import dataclass
from uuid import UUID


class AccountAlreadyExistsError(Exception):
    """Raised when an email is already registered."""


class InvalidCredentialsError(Exception):
    """Raised when authentication fails without exposing which field was invalid."""


class ResourceNotFoundError(Exception):
    """Raised when a resource is absent or outside the actor's visible scope."""


class ForbiddenActionError(Exception):
    """Raised when a visible resource cannot be changed by the actor's role."""


@dataclass(frozen=True)
class TaskVersionConflictError(Exception):
    task_id: UUID
    current_version: int
