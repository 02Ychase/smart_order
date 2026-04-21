from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_FILES = [
    ROOT / "ui/src/views/MerchantDetailView.vue",
    ROOT / "ui/src/views/CheckoutView.vue",
    ROOT / "ui/src/views/AddressView.vue",
    ROOT / "ui/src/views/OrderListView.vue",
    ROOT / "ui/src/views/OrderDetailView.vue",
]


def test_api_error_interceptor_attaches_response_metadata() -> None:
    contents = (ROOT / "ui/src/api/index.js").read_text(encoding="utf-8")

    assert "const requestError = new Error(error.response?.data?.detail || '请求失败，请稍后再试')" in contents
    assert "requestError.status = error.response?.status" in contents
    assert "requestError.data = error.response?.data" in contents
    assert "requestError.payload = error.response?.data" in contents
    assert "throw requestError" in contents


def test_frontend_views_guard_mount_loads_and_detail_fetches() -> None:
    homepage_contents = (ROOT / "ui/src/composables/useHomepage.js").read_text(encoding="utf-8")
    assert "const errorMessage = ref('')" in homepage_contents
    assert "try {" in homepage_contents
    assert "catch (error) {" in homepage_contents
    assert "加载失败，请稍后再试" in homepage_contents

    merchant_list = (ROOT / "ui/src/views/MerchantListView.vue").read_text(encoding="utf-8")
    assert "errorMessage: { type: String, default: '' }" in merchant_list

    for file_path in VIEW_FILES:
        contents = file_path.read_text(encoding="utf-8")
        assert "const errorMessage = ref('')" in contents, str(file_path)
        assert "try {" in contents, str(file_path)
        assert "catch (error) {" in contents, str(file_path)
        assert "加载失败，请稍后再试" in contents, str(file_path)

    merchant_detail = (ROOT / "ui/src/views/MerchantDetailView.vue").read_text(encoding="utf-8")
    assert "if (!merchantId) {" in merchant_detail
    assert "dishes.value = await listMerchantDishes(merchantId)" in merchant_detail
    assert "listMerchantDishes(1)" not in merchant_detail

    order_detail = (ROOT / "ui/src/views/OrderDetailView.vue").read_text(encoding="utf-8")
    assert "const orders = await listOrders()" in order_detail
    assert "const firstOrder = orders[0]" in order_detail
    assert "if (!firstOrder) {" in order_detail
    assert "getOrderDetail(1)" not in order_detail
