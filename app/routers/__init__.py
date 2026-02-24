"""Router exports for FastAPI application.

RU: Экспорт маршрутов приложения.
EN: Export FastAPI routers for app package imports.
"""

from typing import TYPE_CHECKING  # noqa: E402

__all__ = [
    "bmi_pro",
    "foods",
    "premium_week",
    "pro",
    "restaurants",
    "recipes",
    "users",
    "vip",
]


def __getattr__(name: str):  # lazy import submodules to avoid side-effects at package import
    if name in __all__:
        from importlib import import_module

        return import_module(f"app.routers.{name}")
    raise AttributeError(name)


# Help static type checkers know exported names exist without importing at runtime
if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from . import bmi_pro as bmi_pro  # noqa: F401
    from . import foods as foods  # noqa: F401
    from . import premium_week as premium_week  # noqa: F401
    from . import pro as pro  # noqa: F401
    from . import restaurants as restaurants  # noqa: F401
    from . import recipes as recipes  # noqa: F401
    from . import users as users  # noqa: F401
    from . import vip as vip  # noqa: F401
