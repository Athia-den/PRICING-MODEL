import yfinance as yf

def calculate_fair_value(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    current_price = info.get('currentPrice', 0)
    eps = info.get('trailingEps', 0)
    industry_pe = info.get('forwardPE', 15)
    growth_rate = info.get('earningsGrowth', 0.05)
    
    fair_value_pe = eps * industry_pe
    fair_value_peg = eps * (industry_pe * (1 + growth_rate))
    gap_pe = (current_price - fair_value_pe) / fair_value_pe * 100
    
    print(f"===== {ticker} 公允价值分析 =====")
    print(f"当前市价:        ${current_price:.2f}")
    print(f"P/E估值:         ${fair_value_pe:.2f}")
    print(f"PEG估值:         ${fair_value_peg:.2f}")
    print(f"P/E偏差:         {gap_pe:.1f}%")
    
    if gap_pe > 10:
        print("结论: ⚠️  股票可能被高估")
    elif gap_pe < -10:
        print("结论: ✅  股票可能被低估")
    else:
        print("结论: 📊  股票定价合理")

calculate_fair_value("AAPL")
calculate_fair_value("MSFT")
