import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import talib
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(layout="wide")

st.title("📈 Multi-Timeframe Candlestick Pattern Detector with Indicators")

# --- Stock Selection ---
stock = st.text_input("Enter NSE stock symbol (e.g., TATAMOTORS.NS):", "TATAMOTORS.NS").upper()
timeframe = st.selectbox("Select Timeframe:", ["1d", "1h", "15m"])

period_map = {"1d": "1y", "1h": "60d", "15m": "7d"}
interval_map = {"1d": "1d", "1h": "60m", "15m": "15m"}

selected_period = period_map[timeframe]
selected_interval = interval_map[timeframe]

# --- Download Data ---
data_load_state = st.text("Loading data...")
data = yf.download(stock, period=selected_period, interval=selected_interval)
data_load_state.text("Data loaded!")

if data.empty:
    st.error(f"No data found for {stock}. Please check the symbol.")
    st.stop()

# --- Indicators & Patterns ---
data["RSI"] = talib.RSI(data["Close"], timeperiod=14)
data["MACD"], data["MACD_signal"], data["MACD_hist"] = talib.MACD(data["Close"], fastperiod=12, slowperiod=26, signalperiod=9)
data["ADX"] = talib.ADX(data["High"], data["Low"], data["Close"], timeperiod=14)
data["BB_upper"], data["BB_middle"], data["BB_lower"] = talib.BBANDS(data["Close"], timeperiod=20)

data["bullish_engulfing"] = talib.CDLENGULFING(data["Open"], data["High"], data["Low"], data["Close"])
data["morning_star"] = talib.CDLMORNINGSTAR(data["Open"], data["High"], data["Low"], data["Close"], penetration=0.3)
data["three_white_soldiers"] = talib.CDL3WHITESOLDIERS(data["Open"], data["High"], data["Low"], data["Close"])
data["volume_avg"] = data["Volume"].rolling(20).mean()
data["volume_spike"] = data["Volume"] > 1.5 * data["volume_avg"]

# --- Signal Logic ---
data["Buy"] = (
    (data["bullish_engulfing"] > 0) |
    (data["morning_star"] > 0) |
    (data["three_white_soldiers"] > 0)
) & (data["RSI"] < 30) & (data["volume_spike"])

data["Sell"] = data["RSI"] > 70

# --- Support & Resistance ---
data["Support"] = data["Low"].rolling(20).min()
data["Resistance"] = data["High"].rolling(20).max()

# --- Signal Table ---
signal_df = data[(data["Buy"] | data["Sell"])][["Close", "RSI", "MACD", "ADX", "Buy", "Sell"]]
signal_df = signal_df.copy()
signal_df["Signal"] = np.where(signal_df["Buy"], "Buy", "Sell")
signal_df.reset_index(inplace=True)
signal_df = signal_df[["Datetime" if timeframe != "1d" else "Date", "Signal", "Close", "RSI", "MACD", "ADX"]]

st.subheader("🔔 Buy/Sell Signals")
st.dataframe(signal_df)

# --- Export to Excel ---
excel = BytesIO()
with pd.ExcelWriter(excel, engine='xlsxwriter') as writer:
    signal_df.to_excel(writer, index=False, sheet_name="Signals")
    writer.save()
st.download_button(
    label="📥 Download Signal Report",
    data=excel.getvalue(),
    file_name=f"{stock}_{timeframe}_signals.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- Main Price Chart ---
st.subheader("📊 Candlestick Chart with Signals")
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(data.index, data["Close"], label="Close", color="black")

# Buy/Sell markers
buy_signals = data[data["Buy"]]
ax.scatter(buy_signals.index, buy_signals["Close"], marker="^", color="green", label="Buy", s=100)
sell_signals = data[data["Sell"]]
ax.scatter(sell_signals.index, sell_signals["Close"], marker="v", color="red", label="Sell", s=100)

# Support/Resistance
ax.plot(data.index, data["Support"], linestyle="--", color="blue", alpha=0.5, label="Support")
ax.plot(data.index, data["Resistance"], linestyle="--", color="orange", alpha=0.5, label="Resistance")

# Bollinger Bands
ax.plot(data.index, data["BB_upper"], linestyle=":", color="gray", alpha=0.4, label="BB Upper")
ax.plot(data.index, data["BB_middle"], linestyle=":", color="gray", alpha=0.3, label="BB Middle")
ax.plot(data.index, data["BB_lower"], linestyle=":", color="gray", alpha=0.4, label="BB Lower")

ax.set_title(f"{stock} - {timeframe} Signals with Support, Resistance, BB")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# --- MACD Plot ---
st.subheader("📉 MACD")
fig2, ax2 = plt.subplots(figsize=(14, 3))
ax2.plot(data.index, data["MACD"], label="MACD", color="blue")
ax2.plot(data.index, data["MACD_signal"], label="Signal Line", color="orange")
ax2.bar(data.index, data["MACD_hist"], color="gray", label="Histogram")
ax2.legend()
ax2.grid(True)
st.pyplot(fig2)

# --- ADX Plot ---
st.subheader("📈 ADX")
fig3, ax3 = plt.subplots(figsize=(14, 2.5))
ax3.plot(data.index, data["ADX"], label="ADX", color="purple")
ax3.axhline(25, linestyle="--", color="gray", alpha=0.5, label="Threshold")
ax3.legend()
ax3.grid(True)
st.pyplot(fig3)

st.caption("Developed using yfinance, TA-Lib, and Streamlit. 📈")
