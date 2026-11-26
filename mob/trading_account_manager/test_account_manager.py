import pytest

from account_manager import Account, AccountManager


@pytest.fixture
def account_manager():
    acc_manager = AccountManager()
    acc_manager.reg_acc(Account("1", "harry", 10.0, "HKD"))
    acc_manager.reg_acc(Account("2", "sam", 20.0, "HKD"))
    acc_manager.reg_acc(Account("3", "bosco", 15.0, "USD"))
    acc_manager.reg_acc(Account("2", "tim", 30.0, "USD"))
    acc_manager.accounts["3"].active = False
    return acc_manager


########## reg_acc ##########
def test_reg_acc_success():
    acc_manager = AccountManager()
    assert acc_manager.reg_acc(Account("1", "harry", 10.0, "HKD"))
    assert "1" in acc_manager.accounts


def test_reg_acc_fail():
    acc_manager = AccountManager()
    assert acc_manager.reg_acc(Account("", "harry", 10.0, "HKD")) is False
    assert acc_manager.reg_acc(Account("1", "", 10.0, "HKD")) is False
    assert acc_manager.reg_acc(Account("1", "harry", -100, "HKD")) is False
    assert acc_manager.reg_acc(Account("1", "harry", 100, "EUR")) is False


def test_reg_acc_fail_duplicate(account_manager):
    assert account_manager.reg_acc(Account("1", "harry", 10.0, "HKD")) is False


########## deposit_funds ##########
def test_deposit_funds_success(account_manager):
    assert account_manager.deposit_funds("1", 100)
    assert account_manager.accounts["1"].balance == 110.0


def test_deposit_funds_fail(account_manager):
    assert account_manager.deposit_funds("10", 100) is False
    assert account_manager.deposit_funds("1", 0) is False
    assert account_manager.deposit_funds("1", -1) is False
    assert account_manager.deposit_funds("3", 100) is False


########## transfer ##########
def test_transfer_success(account_manager):
    assert account_manager.transfer("1", "2", 10.0)
    assert account_manager.accounts["1"].balance == 0.0
    assert account_manager.accounts["2"].balance == 30.0


def test_transfer_fail(account_manager):
    assert account_manager.transfer("0", "2", 10.0) is False
    assert account_manager.transfer("1", "0", 10.0) is False
    assert account_manager.transfer("1", "1", 10.0) is False
    assert account_manager.transfer("1", "2", -10.0) is False
    assert account_manager.transfer("1", "3", 10.0) is False
    assert account_manager.transfer("1", "4", 10.0) is False
    assert account_manager.transfer("1", "2", 100.0) is False


########## process_batch ##########
def test_process_batch_success(account_manager):
    transfers = [
        ("1", "2", 10.0),
        ("2", "1", 5.0),
    ]

    assert account_manager.process_batch(transfers)
    assert account_manager.accounts["1"] == 5.0
    assert account_manager.accounts["2"] == 25.0


def test_process_batch_fail(account_manager):
    transfers = [
        ("1", "2", 10.0),
        ("2", "2", 5.0),
    ]

    assert account_manager.process_batch(transfers) is False
    assert account_manager.accounts["1"] == 10.0
    assert account_manager.accounts["2"] == 20.0


########## account_summary ##########
def test_account_summary_success(account_manager):
