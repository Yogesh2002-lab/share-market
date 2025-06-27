import yfinance as yf
import pandas as pd
import talib

def get_candlestick_patterns(company_ticker, start_date, end_date):
    try:
        # Download historical data
        # Use auto_adjust=True for adjusted prices, and progress=False for cleaner output
        data = yf.download(company_ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)

        if data.empty:
            print(f"No data found for {company_ticker} between {start_date} and {end_date}.")
            return None

        # --- FIX STARTS HERE ---
        # If columns are MultiIndex, flatten them to a single level
        if isinstance(data.columns, pd.MultiIndex):
            # Option 1: Access the first level of the MultiIndex (usually the OHLCV names)
            data.columns = data.columns.get_level_values(0)
            # Or, if you want to include the ticker, you could do:
            # data.columns = [f"{col[0]}_{col[1]}" for col in data.columns]
            # But for TA-Lib, just the OHLCV name is needed.
        # --- FIX ENDS HERE ---

        # Standardize column names to uppercase
        new_columns = []
        for col in data.columns:
            if isinstance(col, str):
                new_columns.append(col.upper())
            else:
                # Fallback for truly unexpected column types, though less likely now
                new_columns.append(str(col).upper())
        data.columns = new_columns

        # Ensure required columns are present and properly named for TA-Lib
        required_columns = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']

        # Check if all required columns exist after standardization
        if not all(col in data.columns for col in required_columns):
            # As auto_adjust=True makes 'Adj Close' become 'Close', this check is mostly
            # for ensuring the initial data structure from yfinance is as expected.
            print(f"Missing required OHLCV data after standardization for {company_ticker}. "
                  f"Available columns: {data.columns.tolist()}")
            return None

        # Define candlestick patterns to detect
        candlestick_patterns = {
            "CDLDOJI": "Doji",
            "CDLHAMMER": "Hammer",
            "CDLINVERTEDHAMMER": "Inverted Hammer",
            "CDLMORNINGSTAR": "Morning Star",
            "CDLEVENINGSTAR": "Evening Star",
            "CDLENGULFING": "Engulfing",
            "CDLPIERCING": "Piercing Pattern",
            "CDLDARKCLOUDCOVER": "Dark Cloud Cover",
            "CDLHARAMI": "Harami",
            "CDLHARAMICROSS": "Harami Cross",
            "CDL3WHITESOLDIERS": "Three White Soldiers",
            "CDL3BLACKCROWS": "Three Black Crows",
            "CDLDRAGONFLYDOJI": "Dragonfly Doji",
            "CDLGRAVESTONEDOJI": "Gravestone Doji",
            "CDLMARUBOZU": "Marubozu",
            "CDLSHOOTINGSTAR": "Shooting Star",
            "CDLHANGINGMAN": "Hanging Man"
        }

        detected_patterns = []

        # Ensure that the Series passed to TA-Lib functions are numeric
        data['OPEN'] = pd.to_numeric(data['OPEN'], errors='coerce')
        data['HIGH'] = pd.to_numeric(data['HIGH'], errors='coerce')
        data['LOW'] = pd.to_numeric(data['LOW'], errors='coerce')
        data['CLOSE'] = pd.to_numeric(data['CLOSE'], errors='coerce')
        data['VOLUME'] = pd.to_numeric(data['VOLUME'], errors='coerce') # Also coerce volume

        # Drop rows with any NaN values in the OHLCV columns, as TA-Lib functions require non-NaN inputs
        data.dropna(subset=['OPEN', 'HIGH', 'LOW', 'CLOSE'], inplace=True) # Volume sometimes allowed to be NaN

        # Skip if not enough data after dropping NaNs
        if data.shape[0] < 2: # Most patterns need at least 2 candles
            print(f"Not enough valid OHLC data after cleaning for {company_ticker}.")
            return None

        for pattern_func_name, pattern_name in candlestick_patterns.items():
            pattern_function = getattr(talib, pattern_func_name, None)
            if pattern_function:
                # Pass the Series to TA-Lib
                pattern_result = pattern_function(
                    data['OPEN'], data['HIGH'], data['LOW'], data['CLOSE']
                )
                matches = pattern_result[pattern_result != 0]

                for idx in matches.index:
                    date = idx.strftime('%Y-%m-%d')
                    val = pattern_result[idx]
                    pattern_type = "Bullish" if val > 0 else "Bearish"
                    detected_patterns.append({
                        "Date": date,
                        "Pattern": pattern_name,
                        "Type": pattern_type,
                        "Value": val
                    })
            else:
                print(f"Warning: TA-Lib function for {pattern_func_name} not found.")


        if detected_patterns:
            patterns_df = pd.DataFrame(detected_patterns)
            patterns_df.sort_values(by="Date", inplace=True)
            # Remove duplicate entries for the same date and pattern, keeping the first
            patterns_df.drop_duplicates(subset=['Date', 'Pattern'], keep='first', inplace=True)
            return patterns_df
        else:
            print(f"No candlestick patterns detected for {company_ticker}.")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# ▶️ Run analysis for two companies
if __name__ == "__main__":
    # Updated end_date to reflect current time for market data purposes.
    # Note: Market data is typically updated after market close.
    # For live data, you'd typically run this *after* the current day's market close.
    # Using a future date ensures we get all available historical data up to yesterday.
    end_date = "2025-06-27" # Using the provided current date from context

    start_date = "2024-01-01"

    # Example 1: Reliance
    company_name = "Reliance Industries"
    ticker_symbol = "RELIANCE.NS" # Reliance on NSE
    print(f"Fetching candlestick patterns for {company_name} ({ticker_symbol}) from {start_date} to {end_date}...\n")
    patterns = get_candlestick_patterns(ticker_symbol, start_date, end_date)

    if patterns is not None:
        print(f"Candlestick Patterns for {company_name} ({ticker_symbol}):")
        print(patterns.to_string(index=False))
    else:
        print(f"Could not detect patterns for {company_name} ({ticker_symbol}).")

    # Example 2: Apple
    company_name_2 = "Apple Inc."
    ticker_symbol_2 = "AAPL" # Apple on NASDAQ
    print(f"\n--- Another Example: {company_name_2} ({ticker_symbol_2}) ---")
    patterns2 = get_candlestick_patterns(ticker_symbol_2, "2024-03-01", end_date)

    if patterns2 is not None:
        print(f"Candlestick Patterns for {company_name_2} ({ticker_symbol_2}):")
        print(patterns2.to_string(index=False))
    else:
        print(f"Could not detect patterns for {company_name_2} ({ticker_symbol_2}).")
