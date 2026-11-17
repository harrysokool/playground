import pytest

from inventory import Inventory, Product


@pytest.fixture
def inv():
    inventory = Inventory()
    inventory.reg_product(Product("1", "apple", 10.0, 10))
    inventory.reg_product(Product("2", "pear", 15.0, 3))
    inventory.reg_product(Product("3", "nuts", 1.0, 20))
    return inventory


def test_reg_product_success():
    inventory = Inventory()
    assert inventory.reg_product(Product("1", "apple", 10.0, 10))
    assert "1" in inventory


def test_reg_product_fail(inv):
    assert inv.reg_product(Product("1", "apple", 10.0, 10)) is False
    assert inv.reg_product(Product("4", "mango", -10.0, 10)) is False
    assert inv.reg_product(Product("4", "mango", 10.0, -10)) is False


def test_restock_product(inv):
    assert inv.restock_product("1", 10) is True
    assert inv.inventory["1"].quantity == 20
    assert inv.restock_product("4", 10) is False
    assert inv.restock_product("1", -10) is False


def test_process_order(inv):
    test_products = {
        "1": 5,
        "2": 2,
    }

    assert inv.process_order(test_products) is True
    assesrt
