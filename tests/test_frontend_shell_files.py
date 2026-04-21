from pathlib import Path


REQUIRED_FILES = [
    "ui/src/views/LoginView.vue",
    "ui/src/views/MerchantListView.vue",
    "ui/src/views/MerchantDetailView.vue",
    "ui/src/views/CheckoutView.vue",
    "ui/src/views/AddressView.vue",
    "ui/src/views/OrderListView.vue",
    "ui/src/views/OrderDetailView.vue",
]



def test_phase1_frontend_shell_files_exist_and_old_demo_is_removed() -> None:
    for relative_path in REQUIRED_FILES:
        assert Path(relative_path).exists(), relative_path

    app_contents = Path("ui/src/App.vue").read_text(encoding="utf-8")
    header_contents = Path("ui/src/components/home/HomeHeader.vue").read_text(encoding="utf-8")
    assistant_contents = Path("ui/src/components/home/FloatingAssistant.vue").read_text(encoding="utf-8")

    assert "智能点餐助手" not in app_contents
    assert "配送范围查询" not in app_contents
    assert "菜品列表" not in app_contents
    assert "smart_order 智能外卖平台" in header_contents
    assert "智能助手" in assistant_contents
