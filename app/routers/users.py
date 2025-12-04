"""User management API endpoints."""

from __future__ import annotations

import logging
import time
from typing import Callable, List, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.schemas.users import UserCreate, UserRead
from core.db import get_session
from core.models import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])

T = TypeVar("T")


def _execute_with_retry(
    action: Callable[[Session], T], db: Session, fallback: T | None = None
) -> T:
    """Execute a DB action with non-destructive retry on transient failures.

    Attempts the action first with the injected DI session. On OperationalError,
    retries up to 3 times with fresh sessions and exponential backoff, without
    touching the original session or performing any destructive operations.

    Args:
        action: Database operation to execute
        db: FastAPI-injected session (never closed or modified)
        fallback: Optional value to return if all retries fail

    Returns:
        Result of the action or fallback value

    Raises:
        HTTPException: 503 with original error if all retries fail and no fallback
    """
    logger = logging.getLogger(__name__)
    max_retries = 3
    base_delay = 0.1  # 100ms base delay

    # First attempt with injected session
    try:
        return action(db)
    except OperationalError as initial_error:
        logger.warning(
            "Database operation failed, attempting non-destructive retry: %s",
            initial_error,
        )

        from core import db as db_module

        # Non-destructive retry with fresh sessions and exponential backoff
        last_error = initial_error
        for attempt in range(1, max_retries + 1):
            # Exponential backoff: 100ms, 200ms, 400ms
            delay = base_delay * (2 ** (attempt - 1))
            logger.debug(f"Retry attempt {attempt}/{max_retries} after {delay}s delay")
            time.sleep(delay)

            # Create fresh session for retry (DI session remains untouched)
            retry_session = db_module.SessionLocal()
            try:
                result = action(retry_session)
                logger.info(f"Database operation succeeded on retry attempt {attempt}")
                return result
            except OperationalError as retry_error:
                last_error = retry_error
                logger.warning(f"Retry attempt {attempt}/{max_retries} failed: {retry_error}")
            finally:
                # Always close the retry session we created
                retry_session.close()

        # All retries exhausted
        logger.error(
            f"Database operation failed after {max_retries} retries. Last error: {last_error}"
        )

        if fallback is not None:
            logger.info("Returning fallback value after retry exhaustion")
            return fallback

        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable after {max_retries} retries: {str(last_error)}",
        ) from last_error


# NOTE: Destructive database reset operations have been removed from automatic retry logic.
# Any database schema resets or file deletions must be performed out-of-band via:
# - Dedicated admin endpoint with proper authentication and confirmation
# - Maintenance scripts run by operators with explicit data backup procedures
# - Manual intervention during development/testing
#
# Automatic deletion of database files in request handlers is unsafe and has been eliminated.


@router.post("", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> Response:
    """RU: Создаёт нового пользователя. EN: Create a new user entry.

    Returns:
        - HTTP 201 (Created) when a new user is successfully created
        - HTTP 409 (Conflict) when a user with the same email already exists

    Raises:
        HTTPException: 409 if email already exists (duplicate creation attempt)
    """

    def _action(session: Session) -> UserRead:
        # Check for existing user
        existing = session.execute(
            select(User).where(User.email == payload.email)
        ).scalar_one_or_none()
        if existing:
            # Email already exists - return 409 Conflict
            # This prevents duplicate user creation and makes the API semantically correct
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        # Create new user
        user = User(email=payload.email, name=payload.name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return UserRead.model_validate(user)

    user_data = _execute_with_retry(_action, db)

    # Successfully created - return 201
    return Response(
        content=user_data.model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("", response_model=List[UserRead])
def list_users(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
) -> List[UserRead]:
    """RU: Возвращает список пользователей с пагинацией.

    EN: Return paginated list of users.
    """

    def _action(session: Session) -> List[UserRead]:
        rows = session.execute(select(User).order_by(User.id).offset(offset).limit(limit)).scalars()
        return [UserRead.model_validate(row) for row in rows]

    result = _execute_with_retry(_action, db)  # No fallback - fail explicitly if DB unavailable
    return result


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_session)) -> UserRead:
    """RU: Получить пользователя по идентификатору.

    EN: Retrieve a user by identifier.
    """

    def _action(session: Session) -> UserRead:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserRead.model_validate(user)

    return _execute_with_retry(_action, db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_session)) -> Response:
    """RU: Удаляет пользователя. EN: Delete a user by identifier."""

    def _action(session: Session) -> Response:
        user = session.get(User, user_id)
        if user is None:
            # Idempotent: user already deleted (or never existed)
            # Return 204 instead of 404 to make retries safe
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        session.delete(user)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return _execute_with_retry(_action, db)
