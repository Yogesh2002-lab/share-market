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

        # If columns are MultiIndex, flatten them to a single level
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Standardize column names to uppercase
        new_columns = []
        for col in data.columns:
            if isinstance(col, str):
                new_columns.append(col.upper())
            else:
                new_columns.append(str(col).upper())
        data.columns = new_columns

        # Ensure required columns are present and properly named for TA-Lib
        required_columns = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']

        if not all(col in data.columns for col in required_columns):
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
        data['VOLUME'] = pd.to_numeric(data['VOLUME'], errors='coerce')

        # Drop rows with any NaN values in the OHLCV columns, as TA-Lib functions require non-NaN inputs
        data.dropna(subset=['OPEN', 'HIGH', 'LOW', 'CLOSE'], inplace=True)

        if data.shape[0] < 2:
            print(f"Not enough valid OHLC data after cleaning for {company_ticker}.")
            return None

        for pattern_func_name, pattern_name in candlestick_patterns.items():
            pattern_function = getattr(talib, pattern_func_name, None)
            if pattern_function:
                pattern_result = pattern_function(
                    data['OPEN'], data['HIGH'], data['LOW'], data['CLOSE']
                )
                matches = pattern_result[pattern_result != 0]

                for idx in matches.index:
                    date = idx.strftime('%Y-%m-%d')
                    val = pattern_result[idx]
                    pattern_type = "Bullish" if val > 0 else "Bearish"
                    
                    # Get the closing price for the detected pattern date
                    closing_price = data.loc[idx, 'CLOSE']
                    
                    recommendation = ""
                    if pattern_type == "Bullish":
                        recommendation = "Consider Buy"
                    elif pattern_type == "Bearish":
                        recommendation = "Consider Sell"
                    else:
                        recommendation = "Neutral" # For patterns that don't clearly imply buy/sell

                    detected_patterns.append({
                        "Date": date,
                        "Pattern": pattern_name,
                        "Type": pattern_type,
                        "Closing Price": round(closing_price, 2), # Round to 2 decimal places
                        "Recommendation": recommendation,
                        "Value": val # Keep value for debugging/reference if needed
                    })
            else:
                print(f"Warning: TA-Lib function for {pattern_func_name} not found.")

        if detected_patterns:
            patterns_df = pd.DataFrame(detected_patterns)
            patterns_df.sort_values(by="Date", inplace=True)
            patterns_df.drop_duplicates(subset=['Date', 'Pattern'], keep='first', inplace=True)
            return patterns_df
        else:
            print(f"No candlestick patterns detected for {company_ticker}.")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def save_patterns_to_excel(df, company_name, ticker_symbol, filename_prefix="candlestick_patterns"):
    """
    Saves the DataFrame of candlestick patterns to an Excel file.

    Args:
        df (pd.DataFrame): DataFrame containing the detected candlestick patterns.
        company_name (str): The name of the company.
        ticker_symbol (str): The ticker symbol of the company.
        filename_prefix (str): Prefix for the Excel filename.
    """
    if df is not None and not df.empty:
        # Create a filename using the company name and ticker symbol
        safe_company_name = "".join([c for c in company_name if c.isalnum() or c == ' ']).strip()
        safe_ticker_symbol = "".join([c for c in ticker_symbol if c.isalnum()]).strip()
        
        filename = f"{filename_prefix}_{safe_company_name}_{safe_ticker_symbol}.xlsx"
        
        # Add a "Company" column to the DataFrame before saving
        df_to_save = df.copy()
        df_to_save.insert(0, "Company", company_name) # Insert at the beginning

        try:
            # Drop the 'Value' column as it's more for internal logic/debugging than user output
            if 'Value' in df_to_save.columns:
                df_to_save = df_to_save.drop(columns=['Value'])
            df_to_save.to_excel(filename, index=False)
            print(f"Candlestick patterns saved to {filename}")
        except Exception as e:
            print(f"Error saving patterns to Excel for {company_name}: {e}")
    else:
        print(f"No patterns to save to Excel for {company_name}.")


# ▶️ Run analysis for user-input company
if __name__ == "__main__":
    # Use current date as end date for up-to-date analysis
    from datetime import datetime
    end_date = datetime.now().strftime("%Y-%m-%d")

    while True:
        company_name_input = input("Enter the company name (e.g., Reliance Industries, Apple Inc.) or 'exit' to quit: ").strip()
        if company_name_input.lower() == 'exit':
            break

        company_ticker_input = input(f"Enter the ticker symbol for {company_name_input} (e.g., RELIANCE.NS, AAPL): ").strip().upper()
        if not company_ticker_input:
            print("Ticker symbol cannot be empty. Please try again.")
            continue

        start_date_input = input("Enter the start date (YYYY-MM-DD, e.g., 2024-01-01): ").strip()
        # Basic date format validation (can be improved)
        try:
            datetime.strptime(start_date_input, "%Y-%m-%d")
        except ValueError:
            print("Invalid start date format. Using default '2024-01-01'. Please use YYYY-MM-DD.")
            start_date_input = "2024-01-01"


        print(f"\nFetching candlestick patterns for {company_name_input} ({company_ticker_input}) from {start_date_input} to {end_date}...\n")
        
        patterns = get_candlestick_patterns(company_ticker_input, start_date_input, end_date)

        if patterns is not None:
            print(f"Candlestick Patterns for {company_name_input} ({company_ticker_input}):")
            print(patterns.to_string(index=False))
            save_patterns_to_excel(patterns, company_name_input, company_ticker_input)
        else:
            print(f"Could not detect patterns for {company_name_input} ({company_ticker_input}).")
        
        print("\n" + "="*50 + "\n") # Separator for next input
