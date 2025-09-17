"""Pydantic schemas for user endpoints.

RU: Pydantic-схемы для работы с пользователями.
EN: Pydantic schemas powering user CRUD endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict


class UserBase(BaseModel):
    """RU: Базовые поля пользователя. EN: Shared user fields."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """RU: Схема создания пользователя. EN: Payload for creating a user."""

    pass


class UserRead(UserBase):
    """RU: Схема чтения пользователя. EN: Response schema for user endpoints."""

    id: int

    model_config = ConfigDict(from_attributes=True)
