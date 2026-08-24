def run_backtest(data):
    data["Return"] = data["Close"].pct_change()
    
    data["Strategy_Return"] = (data["Signal"].shift(1)*data["Return"])
    
    data["Market"] = (1 + data["Return"]).cumprod()
    
    data["Strategy"] = (1 + data["Strategy_Return"]).cumprod()
    
    return data