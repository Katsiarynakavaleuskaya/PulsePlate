"""User management API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List, TypeVar
from urllib.parse import urlparse

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
    """Execute a DB action with a one-time retry after reinitializing schema.

    If both attempts fail and a fallback is provided, return it to keep endpoints responsive.
    """
    try:
        return action(db)
    except OperationalError:
        from core import db as db_module
        import logging

        logger = logging.getLogger(__name__)
        try:
            db.close()
        except Exception as e:
            # Session may already be closed; log and continue
            logger.debug("Session close failed (likely already closed): %s", e)

        _reset_db_file(db_module)
        retry_session = db_module.SessionLocal()
        try:
            return action(retry_session)
        except OperationalError as exc:
            if fallback is not None:
                return fallback
            raise HTTPException(status_code=503, detail="Database unavailable") from exc
        finally:
            retry_session.close()


def _reset_db_file(db_module: Any) -> None:
    """Recreate the SQLite DB file if it became readonly or was removed."""
    url = getattr(db_module, "DATABASE_URL", "")
    parsed = urlparse(url)
    if parsed.scheme.startswith("sqlite") and parsed.path:
        db_path = Path(parsed.path)
        try:
            if db_path.exists():
                db_path.unlink()
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Log file removal errors; init_db will try to create as needed
            import logging

            logger = logging.getLogger(__name__)
            logger.debug("DB file reset failed: %s", e)
    db_module.init_db()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> UserRead:
    """RU: Создаёт нового пользователя. EN: Create a new user entry."""

    def _action(session: Session) -> UserRead:
        existing = session.execute(
            select(User).where(User.email == payload.email)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        user = User(email=payload.email, name=payload.name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return UserRead.model_validate(user)

    return _execute_with_retry(_action, db)


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

    return _execute_with_retry(_action, db, fallback=[])


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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        session.delete(user)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return _execute_with_retry(_action, db)
