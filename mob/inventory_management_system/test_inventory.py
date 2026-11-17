import pytest

from inventory import Inventory, Product


@pytest.fixture
def test_reg_product():
    inventory = Inventory()
    inventory.reg_product(Product("1", "apple", 10.0, 10))
    inventory.reg_product(Product("2", "pear", 15.0, 3))
    inventory.reg_product(Product("3", "nuts", 1.0, 20))
    return inventory
