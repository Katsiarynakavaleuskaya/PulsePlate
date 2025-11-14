"""
Тесты для покрытия app.py lifespan событий
Покрывает строки: 1505→exit, 1508→exit, 1520-1527, 1606, 1657-1660
"""

from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


class TestAppLifespanCoverage:
    """Тесты для покрытия app.py lifespan событий"""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/health",
            "/docs",
            "/metrics",
            "/openapi.json",
        ],
    )
    def test_app_lifespan_endpoints_accessible(self, test_environment, endpoint: str) -> None:
        """Параметризованный тест доступности endpoints после startup lifespan событий.

        Покрывает базовую проверку, что приложение работает после выполнения
        startup событий lifespan (строки 1520-1527).
        """
        import app

        # Используем context manager для гарантированного выполнения shutdown
        with TestClient(cast(ASGIApp, app.app)) as client:
            response = client.get(endpoint)
            assert (
                response.status_code == 200
            ), f"Endpoint {endpoint} должен возвращать 200 после startup"

    def test_app_lifespan_startup_calls_init_db(self, test_environment) -> None:
        """Тест, что lifespan startup вызывает init_db().

        Покрывает строки 391-395: вызов init_db() при startup.
        """
        import app
        from unittest.mock import patch

        # Patch core.db.init_db before creating TestClient to catch the startup call
        # Note: TestClient automatically triggers lifespan startup when entering context
        with patch("core.db.init_db") as mock_init_db:
            with TestClient(cast(ASGIApp, app.app)) as client:
                # Проверяем, что init_db был вызван при startup
                # Note: init_db is called during lifespan startup, which TestClient triggers
                assert mock_init_db.called, "init_db should be called during lifespan startup"
                # Проверяем, что приложение работает
                response = client.get("/health")
                assert response.status_code == 200

    def test_app_lifespan_startup_calls_validate_template_dir(self, test_environment) -> None:
        """Тест, что lifespan startup вызывает validate_template_dir().

        Покрывает строки 397-404: вызов validate_template_dir() при startup.
        """
        import app

        with patch("app.dependencies.validate_template_dir") as mock_validate:
            # TestClient автоматически запускает lifespan startup
            with TestClient(cast(ASGIApp, app.app)) as client:
                # Проверяем, что validate_template_dir был вызван при startup
                mock_validate.assert_called_once()
                # Проверяем, что приложение работает
                response = client.get("/health")
                assert response.status_code == 200

    def test_app_lifespan_startup_calls_start_background_updates(self, test_environment) -> None:
        """Тест, что lifespan startup вызывает start_background_updates().

        Покрывает строки 406-440: вызов start_background_updates() при startup.
        """
        import app

        with patch("app.start_background_updates") as mock_start:
            # TestClient автоматически запускает lifespan startup
            with TestClient(cast(ASGIApp, app.app)) as client:
                # Проверяем, что start_background_updates был вызван при startup
                mock_start.assert_called_once_with(update_interval_hours=24)
                # Проверяем, что приложение работает
                response = client.get("/health")
                assert response.status_code == 200

    def test_app_lifespan_shutdown_calls_stop_background_updates(self, test_environment) -> None:
        """Тест, что lifespan shutdown вызывает stop_background_updates().

        Покрывает строки 444-462: вызов stop_background_updates() при shutdown.
        """
        import app

        with patch("app.stop_background_updates") as mock_stop:
            # TestClient с context manager гарантирует выполнение shutdown
            with TestClient(cast(ASGIApp, app.app)) as client:
                # Проверяем, что приложение работает до shutdown
                response = client.get("/health")
                assert response.status_code == 200
                # stop_background_updates ещё не должен быть вызван
                assert mock_stop.call_count == 0

            # После выхода из context manager должен быть вызван shutdown
            mock_stop.assert_called_once()

    def test_app_lifespan_context_manager_cleanup(self, test_environment) -> None:
        """Тест корректной работы context manager для lifespan.

        Покрывает строки 1505→exit, 1508→exit: корректное завершение
        lifespan context manager.
        """
        import app

        startup_called = False
        shutdown_called = False

        with (
            patch("core.db.init_db") as mock_init_db,
            patch("app.stop_background_updates") as mock_stop,
        ):
            # TestClient с context manager гарантирует startup и shutdown
            with TestClient(cast(ASGIApp, app.app)) as client:
                # Startup должен быть выполнен
                assert mock_init_db.called
                startup_called = True

                # Проверяем, что приложение работает
                response = client.get("/health")
                assert response.status_code == 200

                # Shutdown ещё не должен быть вызван
                assert not mock_stop.called

            # После выхода из context manager должен быть вызван shutdown
            assert mock_stop.called
            shutdown_called = True

        # Проверяем, что оба события были выполнены
        assert startup_called
        assert shutdown_called

    def test_app_lifespan_startup_error_handling(self, test_environment) -> None:
        """Тест обработки ошибок при startup в lifespan.

        Покрывает строки 391-395, 397-404: обработка ошибок при инициализации.
        """
        import app

        # Тестируем, что ошибка в init_db обрабатывается через fallback
        with patch("core.db.init_db", side_effect=Exception("DB error")):
            # В тестовом окружении fallback должен обработать ошибку
            with TestClient(cast(ASGIApp, app.app)) as client:
                # Приложение должно продолжать работать
                response = client.get("/health")
                assert response.status_code == 200

    def test_app_lifespan_shutdown_error_handling(self, test_environment) -> None:
        """Тест обработки ошибок при shutdown в lifespan.

        Покрывает строки 461-462: обработка ошибок при shutdown.
        """
        import app

        # Тестируем, что ошибка в stop_background_updates не ломает shutdown
        with patch("app.stop_background_updates", side_effect=Exception("Stop error")):
            with TestClient(cast(ASGIApp, app.app)) as client:
                response = client.get("/health")
                assert response.status_code == 200

            # Shutdown должен завершиться без исключения, несмотря на ошибку
            # (ошибка логируется, но не пробрасывается)


class TestAppInitErrorHandling:
    """Test error handling in app initialization."""

    def test_propagate_app_patches_none_source(self) -> None:
        """Test _propagate_app_patches with None source (line 1244)."""
        import app
        from unittest.mock import MagicMock

        # Call with None source should return early
        result = app._propagate_app_patches(None, MagicMock())
        assert result is None

    def test_propagate_app_patches_none_target(self) -> None:
        """Test _propagate_app_patches with None target (line 1244)."""
        import app
        from unittest.mock import MagicMock

        # Call with None target should return early
        result = app._propagate_app_patches(MagicMock(), None)
        assert result is None

    def test_propagate_app_patches_exception(self) -> None:
        """Test _propagate_app_patches exception handling (lines 1250-1251)."""
        import app
        from unittest.mock import MagicMock

        source = MagicMock()

        # Create a target object that raises exception when setting attributes
        from typing import Any

        class FailingTarget:
            def __setattr__(self, name: str, value: Any) -> None:
                raise AttributeError("Cannot set attribute")

        target = FailingTarget()

        # Should not raise exception, just continue
        # The function catches Exception and continues
        try:
            app._propagate_app_patches(source, target)
        except Exception:
            # Should not reach here
            pytest.fail("_propagate_app_patches should not raise exception")

    def test_sync_app_attr_sources_none_alias_module(self) -> None:
        """Test _sync_app_attr_sources with None alias_module (line 1260)."""
        import app
        from unittest.mock import MagicMock

        # Call with None alias_module should return early
        result = app._sync_app_attr_sources(None, (MagicMock(),))
        assert result is None
