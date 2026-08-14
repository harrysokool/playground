from data import load_data


data = load_data(
    "AAPL",
    "2020-01-01",
    "2025-01-01",
)

print(data.head())