import os

from fastapi.testclient import TestClient

from app import app, normalize_flags


def test_normalize_flags():
    """Test the normalize_flags function directly."""
    # Test with the exact data from the failing test
    result = normalize_flags("female", "yes", "no")
    print(f"normalize_flags('female', 'yes', 'no'): {result}")
    print(f"is_pregnant: {result['is_pregnant']}")
    print(f"gender_male: {result['gender_male']}")
    print(f"is_athlete: {result['is_athlete']}")


def test_bmi_endpoint_debug():
    """Debug the BMI endpoint with the exact data from the failing test."""
    os.environ["API_KEY"] = "test_key"
    client = TestClient(app)

    data = {
        "weight_kg": 65.0,
        "height_m": 1.65,
        "age": 28,
        "gender": "female",
        "pregnant": "yes",
        "athlete": "no",
        "lang": "en",
        "include_chart": True
    }

    print(f"Request data: {data}")

    # Test the normalize_flags function with this data
    flags = normalize_flags(data["gender"], data["pregnant"], data["athlete"])
    print(f"Flags from normalize_flags: {flags}")

    response = client.post("/bmi", json=data)
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response JSON: {result}")
        print(f"Group: {result.get('group')}")
        print(f"Category: {result.get('category')}")
        print(f"Note: {result.get('note')}")
        if "visualization" in result:
            print(f"Visualization available: {result['visualization'].get('available')}")
        else:
            print("No visualization key")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    print("=== Testing normalize_flags ===")
    test_normalize_flags()

    print("\n=== Testing BMI endpoint ===")
    test_bmi_endpoint_debug()
