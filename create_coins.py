import sqlite3
import pandas as pd
import glob
import os

# 1. Find all coin_*.csv files
for csv_path in glob.glob("coin_*.csv"):
    # Derive the coin name from the filename, e.g. "coin_Bitcoin.csv" → "Bitcoin"
    fname = os.path.basename(csv_path)
    coin = fname.replace("coin_", "").replace(".csv", "")

    # 2. Read the CSV
    df = pd.read_csv(csv_path)
    # Optional: Parse the Date column as datetime
    df["Date"] = pd.to_datetime(df["Date"])

    # 3. Connect (or create) coin_<name>.db
    db_name = f"{coin.lower()}.db"
    conn = sqlite3.connect(db_name)

    # 4. Write the DataFrame into a table named after the coin, e.g. BITCOIN
    table_name = coin.upper()
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.close()
    print(f"Created {db_name} with table {table_name} ({len(df)} rows).")
