from dataclasses import dataclass


@dataclass
class Product:
    sku: str
    name: str
    price: float
    quantity: int


class Inventory:
    def __init__(self) -> None:
        self.inventory = {}

    def reg_product(self, product: Product) -> bool:
        if product.sku in self.inventory:
            return False

        if product.price < 0 or product.quantity < 0:
            return False

        self.inventory[product.sku] = product
        return True

    def restock_product(self, sku: str, num: int) -> bool:
        if sku not in self.inventory:
            return False

        if num < 0:
            return False

        self.inventory[sku] += num
        return True

    def process_order(self, products: dict) -> bool:
        for sku in products.keys():
            if self.Inventory[sku] < products[sku]:
                return False

        for sku in products.keys():
            self.inventory[sku] -= products[sku]

        return True

    def low_stock_report(self, threshold: int) -> list[Product]:
        pass

    def inventory_value(self) -> float:
        pass
