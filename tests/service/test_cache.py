from service.cache import TieredCache


def test_l1_cache_hit():
    cache = TieredCache(l1_max_size=10)
    cache.set("key1", [0.1, 0.2, 0.3])

    result = cache.get("key1")
    assert result == [0.1, 0.2, 0.3]


def test_l1_cache_miss():
    cache = TieredCache(l1_max_size=10)

    result = cache.get("nonexistent")
    assert result is None


def test_l1_eviction():
    cache = TieredCache(l1_max_size=2)
    cache.set("k1", [1.0])
    cache.set("k2", [2.0])
    cache.set("k3", [3.0])

    assert cache.get("k1") is None
    assert cache.get("k2") == [2.0]
    assert cache.get("k3") == [3.0]


def test_cache_stats():
    cache = TieredCache(l1_max_size=10)
    cache.set("k1", [1.0])
    cache.get("k1")
    cache.get("k2")

    stats = cache.stats()
    assert stats["l1_hits"] == 1
    assert stats["l1_misses"] == 1
