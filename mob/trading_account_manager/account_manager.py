from dataclasses import dataclass


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
        if account_id not in self.accounts:
            return False
        account: Account = self.accounts[account_id]
        if not account.active:
        

    def transfer_funds(self):
        pass

    def process_batch_transfer(self):
        pass

    def acc_summary(self):
        pass

    def total_funds(self):
        pass
