# Is the recent market stronger or weaker than the longer-term market?
def moving_average_strategy(data):
    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()
    
    data["Signal"] =(
        data["MA20"] > data["MA50"]
    ).astype(int)
    
    return data