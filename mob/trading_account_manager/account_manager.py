from dataclasses import dataclass
import copy


@dataclass
class Account:
    account_id: str
    owner_name: str
    balance: float
    currency: str
    active: bool = True


class AccountManager:
    def __init__(self):
        self.accounts = {}

    def validate_acc(self, account: Account) -> bool:
        if account.account_id is None:
            return False
        if account.owner_name is None:
            return False
        if account.balance < 0:
            return False
        if account.currency not in {"HKD", "USD", "EUR"}:
            return False
        if account.account_id in self.accounts:
            return False

    def reg_acc(self, account: Account) -> bool:
        if not self.validate_acc(account):
            return False
        self.accounts[account.account_id] = account
        return True

    def deposit_funds(self, account_id: str, amount: float) -> bool:
        if account_id not in self.accounts or amount <= 0:
            return False
        account: Account = self.accounts[account_id]
        if not account.active:
            return False

        account.balance += amount
        return True

    def transfer(self, from_account_id: str, to_account_id: str, amount: float) -> bool:
        if from_account_id not in self.accounts:
            return False
        if to_account_id not in self.accounts:
            return False
        if from_account_id == to_account_id:
            return False
        if amount <= 0:
            return False
        account1: Account = self.accounts[from_account_id]
        account2: Account = self.accounts[to_account_id]
        if not account1.active or not account2.active:
            return False
        if account1.currency != account2.currency:
            return False
        if account1.balance < amount:
            return False

        account1.balance -= amount
        account2.balance += amount
        return True

    def process_batch(self, transfers: list[tuple[str, str, float]]) -> bool:
        if not transfers:
            return False

        backup = {}
        for account_id in self.accounts:
            account: Account = self.accounts[account_id]
            backup[account_id] = copy.deepcopy(account)

        for from_account_id, to_account_id, amount in transfers:
            if not self.transfer(from_account_id, to_account_id, amount):
                for account_id in backup:
                    self.accounts[account_id] = backup[account_id]
                return False

        return True

    def account_summary(self, currency: str) -> list[tuple[str, float]]:
        if currency not in {"HKD", "USD", "EUR"}:
            return False

        # first get all the active accounts
        accounts = list(filter(lambda x: x.active, self.accounts.values()))
        # then get the account with the right currency
        accounts = list(filter(lambda x: x.currency == currency, accounts))

        res = []
        for account in accounts:
            res.append((account.account_id, account.balance))

        return sorted(res, key=lambda x: (x[1], x[0]))

    def total_funds(self, currency: str) -> float:
        if currency not in {"HKD", "USD", "EUR"}:
            return False

        accounts = list(filter(lambda x: x.active, self.accounts.values()))
        accounts = list(filter(lambda x: x.currency == currency, accounts))

        res = 0.0
        for account in accounts:
            res += account.balance

        return res
