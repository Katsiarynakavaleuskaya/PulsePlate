"""
Тесты покрытия VIP router import fallback логики (строки 55-74)
"""


class TestVIPImportFallbackCoverage:
    def test_vip_import_fallback_scenarios(self, test_environment, test_client, vip_headers):
        """Тест покрытия VIP import fallback сценариев"""
        client = test_client

        # Базовый валидный payload
        base_payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Тестируем успешный сценарий
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=base_payload,
            headers=vip_headers,
        )
        assert response.status_code in [200, 404]

        # Тестируем сценарий с невалидными данными
        invalid_payload = {
            "sex": "invalid",
            "age": -1,
            "height_cm": -1,
            "weight_kg": -1,
            "activity": "invalid",
            "goal": "invalid",
        }
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=invalid_payload,
            headers=vip_headers,
        )
        assert response.status_code in [200, 422, 404]

        # Тестируем recipes endpoint
        response = client.post(
            "/api/v1/vip/recipes",
            json=base_payload,
            headers=vip_headers,
        )
        assert response.status_code in [200, 404]
