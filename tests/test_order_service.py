from src.order_service import OrderItem, OrderRequest, process_order


class FakeClient:
    def __init__(self):
        self.called = False

    def order_update(self, order):
        self.called = True
        return "confirmed"


def test_order_over_cap_is_rejected_before_spending_call():
    fake = FakeClient()
    order = OrderRequest("o-9", "a@example.com", [OrderItem("sku", 1)], 120.0)
    result = process_order(order, 100.0, fake)
    assert result == {"status": "rejected", "reason": "monthly hard cap exceeded", "order_id": "o-9"}
    assert fake.called is False
