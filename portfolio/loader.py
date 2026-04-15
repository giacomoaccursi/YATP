"""Data loading: configuration and transactions."""

import pandas as pd
import json
import sys


def load_config(path):
    """Load the JSON configuration file."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as error:
        print(f"❌ Error parsing {path}: {error}")
        sys.exit(1)


def load_transactions(path):
    """Read the transactions CSV and convert column types."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"❌ Transactions file not found: {path}")
        sys.exit(1)
    except pd.errors.ParserError as error:
        print(f"❌ Error parsing CSV {path}: {error}")
        sys.exit(1)

    df.columns = df.columns.str.strip()

    required_columns = ["Date", "Type", "Security", "Shares", "Quote", "Net Transaction Value"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"❌ Missing columns in CSV: {', '.join(missing)}")
        sys.exit(1)

    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Shares", "Quote", "Net Transaction Value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df
