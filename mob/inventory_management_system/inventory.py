from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

hkt = timezone(timedelta(hours=8), name="HKT")


@dataclass
class Product:
    sku: str
    name: str
    price: float
    quantity: int


class Inventory:
    def __init__(self) -> None:
        self.inventory = {}
        self.history: dict[str, list[str]] = {}

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

        product: Product = self.inventory[sku]
        product.quantity += num
        self._log(product.sku, "restock", num)

        return True

    def process_order(self, products: dict) -> bool:
        if not products:
            return False

        for sku in products.keys():
            if sku not in self.inventory or products[sku] <= 0:
                return False
            product: Product = self.inventory[sku]
            if product.quantity < products[sku]:
                return False

        for sku in products.keys():
            product: Product = self.inventory[sku]
            product.quantity -= products[sku]
            self._log(product.sku, "reduce", products[sku])

        return True

    def low_stock_report(self, threshold: int) -> list[tuple[str, int]]:
        res = []

        for sku in self.inventory:
            product: Product = self.inventory[sku]
            if product.quantity < threshold:
                res.append((product.name, product.quantity))

        return sorted(res, key=lambda x: x[1])

    def inventory_value(self) -> float:
        total_value = 0

        for sku in self.inventory:
            product: Product = self.inventory[sku]
            total_value += product.quantity * product.price

        return total_value

    def _log(self, sku: str, action: str, qty: int) -> None:
        ts = datetime.now(hkt).strftime("%d-%m-%Y %H:%M")
        self.history.setdefault(sku, []).append(f"[{ts}] {action}: {qty}")

    def transaction_history(self, sku: str):
        return self.history.get(sku, [])
