import yfinance as yf


def load_data(ticker: str, start: str, end: str):
    data = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )

    if hasattr(data.columns, "levels"):
        data.columns = data.columns.get_level_values(0)

    return data