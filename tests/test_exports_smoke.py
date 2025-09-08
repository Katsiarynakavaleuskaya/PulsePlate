from core.exports import to_csv_day, to_csv_week


def test_to_csv_day_smoke():
    plan = {
        "meals": [
            {
                "name": "Breakfast",
                "food_item": "Oatmeal",
                "kcal": 300,
                "protein_g": 10,
                "carbs_g": 50,
                "fat_g": 5,
            },
            {
                "name": "Lunch",
                "food_item": "Chicken",
                "kcal": 500,
                "protein_g": 35,
                "carbs_g": 30,
                "fat_g": 20,
            },
        ],
        "total_kcal": 800,
        "total_protein": 45,
        "total_carbs": 80,
        "total_fat": 25,
    }
    data = to_csv_day(plan)
    assert isinstance(data, (bytes, bytearray))
    s = data.decode("utf-8")
    assert "Meal,Food Item,Calories,Protein (g),Carbs (g),Fat (g)" in s
    assert "Total" in s


def test_to_csv_week_smoke():
    week = {
        "daily_menus": [
            {
                "date": "day_1",
                "meals": [
                    {
                        "name": "Breakfast",
                        "food_item": "Oats",
                        "kcal": 300,
                        "protein_g": 10,
                        "carbs_g": 50,
                        "fat_g": 5,
                        "cost": 1.5,
                    },
                ],
            }
        ],
        "shopping_list": {"oats": 500},
        "total_cost": 10.0,
        "adherence_score": 90.0,
    }
    data = to_csv_week(week)
    assert isinstance(data, (bytes, bytearray))
    s = data.decode("utf-8")
    assert "Day,Meal,Food Item,Calories,Protein (g),Carbs (g),Fat (g),Cost" in s
    assert "Shopping List" in s
    assert "Weekly Summary" in s
