import os
import tempfile

from faker import Faker

fake = Faker()


class TestFoodDbNewMissingLines:
    """Targeted tests for core/food_db_new.py lines 91-103 and 115-119."""

    def setup_method(self):
        Faker.seed(42)
        # Minimal CSV fixture for FoodDB
        self.test_csv_content = (
            "name,group,per_g,protein_g,fat_g,carbs_g,fiber_g,Fe_mg,Ca_mg,VitD_IU,B12_ug,Folate_ug,Iodine_ug,K_mg,Mg_mg,flags,price\n"
            "lentils,legumes,1.0,9.0,0.4,20.0,7.9,3.3,19.0,0.0,0.0,181.0,0.0,369.0,36.0,VEG;GF,2.50\n"
            "spinach,vegetables,1.0,2.9,0.4,3.6,2.2,2.7,99.0,0.0,0.0,194.0,0.0,558.0,79.0,VEG;GF,3.00\n"
            "chicken_breast,meat,1.0,31.0,3.6,0.0,0.0,0.9,15.0,0.0,0.3,4.0,0.0,256.0,28.0,OMNI,8.50\n"
            "salmon,fish,1.0,25.0,11.0,0.0,0.0,0.8,12.0,360.0,4.8,25.0,0.0,363.0,29.0,OMNI;PESC,15.00\n"
            "tofu,soy,1.0,8.1,4.8,1.9,0.3,5.4,350.0,0.0,0.0,15.0,0.0,121.0,53.0,VEG;GF,4.20\n"
            "greek_yogurt,dairy,1.0,10.0,0.4,3.6,0.0,0.1,110.0,0.0,0.5,7.0,0.0,141.0,11.0,VEG,5.50\n"
            "oats,grains,1.0,16.9,6.9,66.3,10.6,4.7,54.0,0.0,0.0,56.0,0.0,429.0,177.0,VEG,1.80\n"
            "banana,fruits,1.0,1.1,0.3,22.8,2.6,0.3,5.0,0.0,0.0,20.0,0.0,358.0,27.0,VEG;GF,1.20\n"
            "eggs,eggs,1.0,13.0,11.0,1.1,0.0,1.8,56.0,41.0,0.9,47.0,24.0,138.0,12.0,VEG,3.40\n"
            "bread_gluten,grains,1.0,8.0,1.0,49.0,2.7,2.7,41.0,0.0,0.0,43.0,0.0,115.0,22.0,VEG,2.10\n"
        )
        self.temp_csv = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.temp_csv.write(self.test_csv_content)
        self.temp_csv.close()

    def teardown_method(self):
        if os.path.exists(self.temp_csv.name):
            os.unlink(self.temp_csv.name)

    def test_pick_booster_item_not_found_line_91(self):
        """For VitD_IU with VEG diet: salmon is incompatible and 'eggs?' is missing → None."""
        from core.food_db_new import FoodDB

        db = FoodDB(self.temp_csv.name)
        assert db.pick_booster_for("VitD_IU", ["VEG"]) is None

    def test_pick_booster_return_candidate_line_94(self):
        """Return first compatible donor for various micronutrients."""
        from core.food_db_new import FoodDB

        db = FoodDB(self.temp_csv.name)
        cases = [
            ("Fe_mg", [], "lentils"),
            ("Ca_mg", ["VEG"], "greek_yogurt"),
            ("B12_ug", ["PESC"], "greek_yogurt"),
            ("Folate_ug", ["VEG"], "spinach"),
            ("K_mg", [], "banana"),
            ("Mg_mg", ["VEG"], "oats"),
        ]
        for micro, diet, expected in cases:
            assert db.pick_booster_for(micro, diet) == expected

    def test_compatible_rules_lines_99_103(self):
        """Cover VEG/OMNI, PESC/OMNI, GF rules."""
        from core.food_db_new import FoodDB

        db = FoodDB(self.temp_csv.name)
        assert db._compatible(["OMNI"], ["VEG"]) is False  # VEG vs OMNI
        assert db._compatible(["OMNI", "PESC"], ["PESC"]) is False  # PESC vs OMNI
        assert db._compatible(["VEG"], ["GF"]) is False  # GF requires GF
        assert db._compatible(["VEG", "GF"], ["GF"]) is True

    def test_aggregate_shopping_price_calc_115_119(self):
        """Verify price scaling per 100g and rounding."""
        from core.food_db_new import FoodDB

        db = FoodDB(self.temp_csv.name)
        days = [
            {"meals": [{"grams": {"lentils": 200, "salmon": 150, "tofu": 100}}]},
            {"meals": [{"grams": {"lentils": 100, "greek_yogurt": 250}}]},
        ]
        result = db.aggregate_shopping(days, lang="en")
        price = {x["name"]: x["price_est"] for x in result}
        assert price["lentils"] == 7.50  # 2.5 per 100g * 300g
        assert price["salmon"] == 22.50  # 15 per 100g * 150g
        assert price["tofu"] == 4.20
        assert price["greek_yogurt"] == 13.75  # 5.5 per 100g * 250g

    def test_no_price_items_are_zero(self):
        """Items without price must yield price_est 0.0."""
        from core.food_db_new import FoodDB as _FDB

        csv_no_price = (
            "name,group,per_g,protein_g,fat_g,carbs_g,fiber_g,Fe_mg,Ca_mg,VitD_IU,B12_ug,Folate_ug,Iodine_ug,K_mg,Mg_mg,flags,price\n"
            "no_price_item,test,1.0,10.0,5.0,15.0,3.0,2.0,50.0,0.0,0.0,100.0,0.0,200.0,30.0,VEG,\n"
            "expensive_item,test,1.0,20.0,10.0,5.0,1.0,3.0,80.0,0.0,0.0,50.0,0.0,300.0,40.0,VEG,12.99\n"
        )
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        try:
            tmp.write(csv_no_price)
            tmp.close()
            db = _FDB(tmp.name)
            out = db.aggregate_shopping(
                [{"meals": [{"grams": {"no_price_item": 100, "expensive_item": 50}}]}]
            )
            by_name = {x["name"]: x for x in out}
            assert by_name["no_price_item"]["price_est"] == 0.0
            assert by_name["expensive_item"]["price_est"] == round(12.99 * 0.5, 2)
        finally:
            os.unlink(tmp.name)

    def test_realistic_shopping_scenarios(self):
        """Smoke realistic basket aggregation with randomized meals."""
        from core.food_db_new import FoodDB

        db = FoodDB(self.temp_csv.name)
        for _ in range(2):
            days = []
            for _d in range(fake.random_int(min=1, max=3)):
                meals = []
                for _m in range(fake.random_int(min=1, max=3)):
                    foods = fake.random_elements(
                        elements=list(db.items.keys()),
                        length=fake.random_int(min=1, max=3),
                        unique=True,
                    )
                    grams = {name: fake.random_int(min=50, max=300) for name in foods}
                    meals.append({"grams": grams})
                days.append({"meals": meals})

            out = db.aggregate_shopping(days, lang="en")
            assert isinstance(out, list)
            for item in out:
                assert {"name", "name_translated", "grams", "price_est"}.issubset(item.keys())
                assert isinstance(item["grams"], (int, float))
                assert isinstance(item["price_est"], (int, float))
                assert item["price_est"] >= 0
