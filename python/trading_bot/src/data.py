import yfinance as yf


def load_data(symbol: str, start: str, end: str):
    return yf.download(
        symbol,
        start=start,
        end=end,
        auto_adjust=True
    )