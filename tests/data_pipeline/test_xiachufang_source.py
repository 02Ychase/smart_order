import json

from data_pipeline.sources.xiachufang import XiaChuFangDishSource, extract_xiachufang_record


def test_extract_xiachufang_record_handles_common_keys():
    raw = {
        "id": "r1",
        "name": "番茄炒蛋",
        "desc": "经典家常菜",
        "ingredients": ["番茄", "鸡蛋", "食盐"],
        "tags": ["家常菜"],
    }

    dish = extract_xiachufang_record(raw)

    assert dish.source == "xiachufang"
    assert dish.source_id == "r1"
    assert dish.name == "番茄炒蛋"
    assert dish.ingredients == ["番茄", "鸡蛋", "食盐"]


def test_source_reads_jsonl(tmp_path):
    path = tmp_path / "recipes.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"id": "1", "name": "番茄炒蛋", "ingredients": ["番茄", "鸡蛋"]}),
            json.dumps({"id": "2", "name": "红烧牛肉", "ingredients": ["牛肉", "酱油"]}),
        ]),
        encoding="utf-8",
    )
    source = XiaChuFangDishSource(path)

    dishes = list(source.fetch(limit=2))

    assert [d.name for d in dishes] == ["番茄炒蛋", "红烧牛肉"]


def test_source_reads_json_array(tmp_path):
    path = tmp_path / "recipes.json"
    path.write_text(
        json.dumps([
            {"id": "1", "name": "番茄炒蛋", "ingredients": ["番茄", "鸡蛋"]},
            {"id": "2", "name": "红烧牛肉", "ingredients": ["牛肉", "酱油"]},
        ]),
        encoding="utf-8",
    )
    source = XiaChuFangDishSource(path)

    dishes = list(source.fetch(limit=1))

    assert len(dishes) == 1
    assert dishes[0].name == "番茄炒蛋"
