"""User management API endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import get_session
from core.models import User
from app.schemas.users import UserCreate, UserRead

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> UserRead:
    """RU: Создаёт нового пользователя. EN: Create a new user entry."""

    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(email=payload.email, name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    result: UserRead = UserRead.model_validate(user)
    return result


@router.get("", response_model=List[UserRead])
def list_users(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
) -> List[UserRead]:
    """RU: Возвращает список пользователей с пагинацией.

    EN: Return paginated list of users.
    """

    rows = db.execute(select(User).order_by(User.id).offset(offset).limit(limit)).scalars()
    results: List[UserRead] = [UserRead.model_validate(row) for row in rows]
    return results


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_session)) -> UserRead:
    """RU: Получить пользователя по идентификатору.

    EN: Retrieve a user by identifier.
    """

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    result: UserRead = UserRead.model_validate(user)
    return result


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_session)) -> Response:
    """RU: Удаляет пользователя. EN: Delete a user by identifier."""

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
