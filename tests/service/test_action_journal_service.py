from service.action_journal_service import ActionJournalService


class InMemoryRepo:
    def __init__(self):
        self.records = []

    def create(self, **kwargs):
        record = {"id": len(self.records) + 1, **kwargs}
        self.records.append(record)
        return record

    def find_last_undoable(self, user_id):
        for record in reversed(self.records):
            if record["user_id"] == user_id and record["undo_policy"] != "not_undoable" and record["status"] == "completed":
                return record
        return None

    def mark_undone(self, action_id):
        for record in self.records:
            if record["action_id"] == action_id:
                record["status"] = "undone"
                return record
        return None


def test_action_journal_records_snapshot_action() -> None:
    service = ActionJournalService(repository=InMemoryRepo())

    record = service.record_completed_action(
        session_id="s1",
        user_id=9,
        action_type="cart_clear",
        undo_policy="snapshot_restore",
        before_snapshot={"items": [{"dish_id": 11, "quantity": 1}]},
        after_snapshot={"items": []},
        undo_tool="restore_cart_snapshot",
        natural_summary="清空购物车",
    )

    assert record["action_id"].startswith("act_")
    assert record["undo_policy"] == "snapshot_restore"


def test_action_journal_finds_last_undoable_action() -> None:
    repo = InMemoryRepo()
    service = ActionJournalService(repository=repo)
    service.record_completed_action("s1", 9, "cart_clear", "snapshot_restore", {"items": [1]}, {"items": []}, "restore_cart_snapshot", "清空购物车")

    record = service.find_last_undoable(user_id=9)

    assert record["action_type"] == "cart_clear"
