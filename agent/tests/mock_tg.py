import json
import os

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_fixture(name="mock_graph.json") -> dict:
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as f:
        return json.load(f)


class FakeTigerGraph:
    """Offline stand-in for TigerGraphMCP backed by mock_graph.json."""

    def __init__(self, fixture: dict = None):
        self.data = fixture or load_fixture()
        self.calls = 0
        self.use_mcp = False

    @property
    def conn(self):
        raise RuntimeError("tests never open a real TigerGraph connection")

    def run_installed_query(self, name: str, params: dict):
        self.calls += 1
        fx = self.data
        if name == "get_transaction_device":
            return [{"Devices": fx["device"]}]
        if name == "get_card_transactions":
            return [{"Txns": fx["card_transactions"]}]
        if name == "get_card_recent_window":
            return [{"Txns": fx["window_txns"]}]
        if name == "get_shared_device_cards":
            return [{"Cards": fx["shared_device_cards"]}]
        if name == "get_customer_cards":
            return [{"Cards": fx["customer_cards"]}]
        return []

    def run_interpreted_query(self, gsql: str, params: dict = None):
        self.calls += 1
        params = params or {}
        if "Transaction:t WHERE t.txn_id" in gsql:
            return [{"T": self.data["transaction"]}]
        if "Card:c -(MADE" in gsql:
            return [{"C": self.data["card"]}]
        return []

    def close(self):
        pass