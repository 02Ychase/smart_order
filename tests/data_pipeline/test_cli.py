import json

from data_pipeline.cli import main, read_jsonl, write_jsonl
from data_pipeline.models import RawDish, RawMerchant


def test_jsonl_round_trip_dataclasses(tmp_path):
    path = tmp_path / "records.jsonl"
    records = [
        RawDish(
            source="xiachufang", source_id="1", name="A", description="desc",
            ingredients=["rice"], tags=[], cuisine_type="", price=None, raw={},
        )
    ]

    write_jsonl(path, records)
    loaded = list(read_jsonl(path))

    assert loaded[0]["name"] == "A"
    assert loaded[0]["ingredients"] == ["rice"]


def test_cli_load_db_dry_run_prints_summary(tmp_path, capsys):
    merchants = tmp_path / "merchants.jsonl"
    dishes = tmp_path / "dishes.jsonl"
    merchants.write_text(json.dumps({
        "source": "amap", "source_id": "m1", "name": "Shop", "city": "Shanghai", "district": "Jingan",
        "address": "1 Road", "longitude": 121.1, "latitude": 31.1, "category": "Food", "phone": "",
        "rating": 4.5, "tags": [], "raw": {}
    }) + "\n", encoding="utf-8")
    dishes.write_text(json.dumps({
        "source": "xiachufang", "source_id": "d1", "name": "Dish", "description": "desc",
        "ingredients": ["rice"], "tags": [], "cuisine_type": "", "price": None, "raw": {}
    }) + "\n", encoding="utf-8")

    exit_code = main(["load-db", "--merchants", str(merchants), "--dishes", str(dishes), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "merchants=1" in captured.out
    assert "dishes=1" in captured.out


def test_read_jsonl_handles_utf8_bom(tmp_path):
    path = tmp_path / "bom.jsonl"
    payload = json.dumps({"name": "Test", "ingredients": ["rice"]})
    path.write_text("﻿" + payload + "\n", encoding="utf-8")

    records = list(read_jsonl(path))

    assert len(records) == 1
    assert records[0]["name"] == "Test"
