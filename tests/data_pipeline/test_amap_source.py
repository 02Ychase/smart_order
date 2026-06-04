from data_pipeline.sources.amap import AmapMerchantSource, parse_amap_poi


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.pages.pop(0))


def test_parse_amap_poi_extracts_required_fields():
    poi = {
        "id": "B001",
        "name": "Sample Hotpot",
        "cityname": "Shanghai",
        "adname": "Jingan",
        "address": "88 Test Road",
        "location": "121.455,31.229",
        "type": "Food;Hotpot",
        "tel": "021-11111111",
        "biz_ext": {"rating": "4.7"},
        "tag": "hotpot,late night",
    }

    merchant = parse_amap_poi(poi)

    assert merchant.source == "amap"
    assert merchant.source_id == "B001"
    assert merchant.name == "Sample Hotpot"
    assert merchant.longitude == 121.455
    assert merchant.latitude == 31.229
    assert merchant.rating == 4.7
    assert "hotpot" in merchant.tags
    assert "late night" in merchant.tags


def test_source_fetches_until_limit():
    session = FakeSession([
        {
            "status": "1",
            "pois": [
                {"id": "B001", "name": "A", "cityname": "Shanghai", "adname": "A1", "address": "x", "location": "1,2", "type": "Food"},
                {"id": "B002", "name": "B", "cityname": "Shanghai", "adname": "A2", "address": "y", "location": "3,4", "type": "Food"},
            ],
        },
        {
            "status": "1",
            "pois": [
                {"id": "B003", "name": "C", "cityname": "Shanghai", "adname": "A3", "address": "z", "location": "5,6", "type": "Food"},
            ],
        },
    ])
    source = AmapMerchantSource(api_key="key", session=session)

    merchants = list(source.fetch(city="Shanghai", keywords=["restaurant"], limit=3, page_size=2))

    assert [m.source_id for m in merchants] == ["B001", "B002", "B003"]
    assert len(session.calls) == 2
    assert session.calls[0][1]["extensions"] == "all"
