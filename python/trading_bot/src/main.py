from data import load_data
from strategy import moving_average_strategy
from backtest import run_backtest


data = load_data(
    "NVDA",
    "2020-01-01",
    "2025-01-01",
)

data = moving_average_strategy(data)

data = run_backtest(data)

market_return = data["Market"].iloc[-1] - 1
strat_return = data["Strategy"].iloc[-1] - 1

print(f"Market Return: {market_return:.2%}")
print(f"Strategy Return: {strat_return:.2%}")