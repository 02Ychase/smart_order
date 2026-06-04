from data_pipeline.sources.menustat import iter_menustat_csv
from data_pipeline.sources.themealdb import parse_themealdb_meal


def test_menustat_csv_reader_extracts_menu_item(tmp_path):
    path = tmp_path / "menustat.csv"
    path.write_text(
        "item_name,restaurant,food_category,calories\nGrilled Chicken,Sample Chain,Entree,450\n",
        encoding="utf-8",
    )

    dishes = list(iter_menustat_csv(path, limit=1))

    assert dishes[0].source == "menustat"
    assert dishes[0].name == "Grilled Chicken"
    assert "Sample Chain" in dishes[0].description


def test_themealdb_parser_collects_ingredients():
    meal = {
        "idMeal": "52772",
        "strMeal": "Teriyaki Chicken",
        "strInstructions": "Cook chicken with sauce.",
        "strCategory": "Chicken",
        "strArea": "Japanese",
        "strIngredient1": "Chicken",
        "strMeasure1": "500g",
        "strIngredient2": "Soy Sauce",
        "strMeasure2": "2 tbsp",
    }

    dish = parse_themealdb_meal(meal)

    assert dish.source == "themealdb"
    assert dish.name == "Teriyaki Chicken"
    assert dish.ingredients == ["Chicken", "Soy Sauce"]
    assert dish.cuisine_type == "Japanese"
