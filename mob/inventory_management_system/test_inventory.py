import pytest

from inventory import Inventory, Product


@pytest.fixture
def inv():
    inventory = Inventory()
    inventory.reg_product(Product("1", "apple", 10.0, 10))
    inventory.reg_product(Product("2", "pear", 15.0, 3))
    inventory.reg_product(Product("3", "nuts", 1.0, 20))
    return inventory


########### reg_product ###########
def test_reg_product_success():
    inventory = Inventory()
    assert inventory.reg_product(Product("1", "apple", 10.0, 10))
    assert "1" in inventory


def test_reg_product_fail(inv):
    assert inv.reg_product(Product("1", "apple", 10.0, 10)) is False
    assert inv.reg_product(Product("4", "mango", -10.0, 10)) is False
    assert inv.reg_product(Product("4", "mango", 10.0, -10)) is False


########### restock_product ###########
def test_restock_product(inv):
    assert inv.restock_product("1", 10) is True
    assert inv.inventory["1"].quantity == 20
    assert inv.restock_product("4", 10) is False
    assert inv.restock_product("1", -10) is False


########### process_order ###########
def test_process_order_success(inv):
    test_products = {
        "1": 5,
        "2": 2,
    }

    assert inv.process_order(test_products) is True
    assert inv.inventory["1"].quantity == 5
    assert inv.inventory["2"].quantity == 1


def test_process_order_fail_sku_not_found(inv):
    test_products = {
        "4": 2,
    }

    assert inv.process_order(test_products) is False


def test_process_order_fail_empty_product(inv):
    test_products = {}

    assert inv.process_order(test_products) is False


def test_process_order_fail_invalid_qty(inv):
    test_products = {
        "1": -5,
        "2": 2,
    }

    assert inv.process_order(test_products) is False
    assert inv.inventory["1"].quantity == 10
    assert inv.inventory["2"].quantity == 3


########### low_stock_report ###########
@pytest.mark.parametrize(
    "threshold, expected",
    [
        (11, [("pear", 3), ("apple", 10)]),
        (10, [("pear", 3)]),
    ],
)
def test_low_stock_report(inv, threshold, expected):
    report = inv.low_stock_report(threshold)
    assert report == expected


########### inventory_value ###########
def test_inventory_value(inv):
    value = inv.inventory_value()
    assert value == 165.0
