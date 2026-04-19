"""User management API endpoints."""

from __future__ import annotations

import logging
import time
from typing import Callable, List, TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.routers.api_key import api_key_header
from app.schemas.users import UserCreate, UserRead
from core import db as db_module
from core.models import User
from core.utils import resolve_attr

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _require_users_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Validate app-level API key access for the users CRUD surface."""
    app_get_api_key = resolve_attr("get_api_key", None)
    if not callable(app_get_api_key):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        )
    try:
        result = app_get_api_key(api_key)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Users API key validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        ) from exc
    if not isinstance(result, str):
        logger.error("Users API key guard returned non-string result")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation unavailable",
        )
    return result


router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(_require_users_api_key)],
)


def _to_user_read(model: User) -> UserRead:
    """Convert SQLAlchemy User model to Pydantic UserRead schema."""
    # NOTE: model_validate() returns Any for mypy; assign to local to keep return type
    result: UserRead = UserRead.model_validate(model)
    return result


def _execute_with_retry(action: Callable[[Session], T], fallback: T | None = None) -> T:
    """Execute a DB action with non-destructive retry on transient failures.

    Creates fresh sessions for all attempts (including first) to maintain thread safety.
    Retries up to 3 times with exponential backoff on OperationalError.

    Args:
        action: Database operation to execute
        fallback: Optional value to return if all retries fail

    Returns:
        Result of the action or fallback value

    Raises:
        HTTPException: 503 with original error if all retries fail and no fallback
    """
    max_retries = 3
    base_delay = 0.1  # 100ms base delay
    last_error: Exception | None = None
    session_factory = db_module.get_session_factory()

    # First attempt with fresh session (thread-safe)
    session = session_factory()
    try:
        return action(session)
    except HTTPException:
        # HTTPException raised by action should propagate immediately without retry
        session.rollback()
        raise
    except IntegrityError:
        # IntegrityError indicates constraint violation (unique, FK, check)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data conflict: resource already exists or violates constraints",
        )
    except OperationalError as initial_error:
        logger.warning(
            "Database operation failed: %s",
            initial_error,
        )
        last_error = initial_error
    finally:
        session.close()

    # Removed automatic database initialization to prevent request handlers from performing schema initialization.
    # Schema should be initialized via test fixtures, setup code, or dedicated migration/startup scripts.

    # Non-destructive retry with fresh sessions and exponential backoff
    for attempt in range(1, max_retries + 1):
        # Exponential backoff: 100ms, 200ms, 400ms
        delay = base_delay * (2 ** (attempt - 1))
        logger.debug("Retry attempt %s/%s after %ss delay", attempt, max_retries, delay)
        time.sleep(delay)

        # Create fresh session for retry
        retry_session = session_factory()
        try:
            result = action(retry_session)
            logger.info("Database operation succeeded on retry attempt %s", attempt)
            return result
        except HTTPException:
            # HTTPException raised by action should propagate immediately without retry
            retry_session.rollback()
            raise
        except IntegrityError:
            retry_session.rollback()
            # Surface immediately; IntegrityError is not retriable in this flow
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Data conflict: resource already exists or violates constraints",
            )
        except OperationalError as retry_error:
            last_error = retry_error
            logger.warning("Retry attempt %s/%s failed: %s", attempt, max_retries, retry_error)
        finally:
            # Always close the retry session we created
            retry_session.close()

    # All retries exhausted
    logger.error(
        "Database operation failed after %s retries. Last error: %s", max_retries, last_error
    )

    if fallback is not None:
        logger.info("Returning fallback value after retry exhaustion")
        return fallback

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database temporarily unavailable. Please try again later.",
    ) from last_error


# NOTE: Destructive database reset operations have been removed from automatic retry logic.
# Any database schema resets or file deletions must be performed out-of-band via:
# - Dedicated admin endpoint with proper authentication and confirmation
# - Maintenance scripts run by operators with explicit data backup procedures
# - Manual intervention during development/testing
#
# Automatic deletion of database files in request handlers is unsafe and has been eliminated.

# TODO: Localize error messages using t(lang, "translation_key") for i18n support
#       (English, Russian, Spanish). Currently hard-coded English strings in detail messages.
#       Consider adding lang parameter or translating at HTTP layer per coding guidelines.


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate) -> UserRead:
    """RU: Создаёт нового пользователя. EN: Create a new user entry.

    Returns:
        - HTTP 201 (Created) when a new user is successfully created
        - HTTP 409 (Conflict) when a user with the same email already exists

    Raises:
        HTTPException: 409 if email already exists (duplicate creation attempt)
    """

    def _action(session: Session) -> UserRead:
        # Create new user
        user = User(email=payload.email, name=payload.name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return _to_user_read(user)

    return cast(UserRead, await run_in_threadpool(_execute_with_retry, _action))


@router.get("", response_model=List[UserRead])
async def list_users(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[UserRead]:
    """RU: Возвращает список пользователей с пагинацией.

    EN: Return paginated list of users.
    """

    def _action(session: Session) -> List[UserRead]:
        # Use database-level pagination for efficiency
        query = select(User).order_by(User.id).offset(offset).limit(limit)
        page_rows = session.execute(query).scalars().all()
        return [_to_user_read(row) for row in page_rows]

    return cast(
        List[UserRead],
        await run_in_threadpool(_execute_with_retry, _action),
    )  # No fallback - fail explicitly if DB unavailable


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int) -> UserRead:
    """RU: Получить пользователя по идентификатору.

    EN: Retrieve a user by identifier.
    """

    def _action(session: Session) -> UserRead:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return _to_user_read(user)

    return cast(UserRead, await run_in_threadpool(_execute_with_retry, _action))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int) -> Response:
    """RU: Удаляет пользователя. EN: Delete a user by identifier.

    Uses retry logic with idempotent design (returns 204 for already-deleted users).
    """

    def _action(session: Session) -> Response:
        user = session.get(User, user_id)
        if user is None:
            # Idempotent: user already deleted (or never existed)
            # Return 204 to make retries safe
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        session.delete(user)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return cast(Response, await run_in_threadpool(_execute_with_retry, _action))
