from helpers import load_data


def test_load_data():
    data = load_data("orders.json")
    assert data != None
    assert len(data) != 0
