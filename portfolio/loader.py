"""Data loading: configuration and transactions."""

import pandas as pd
import json


def load_config(path):
    """Load the JSON configuration file.

    Raises FileNotFoundError or ValueError on failure.
    """
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")
    except json.JSONDecodeError as error:
        raise ValueError(f"Error parsing {path}: {error}")


def load_transactions(path):
    """Read the transactions CSV and convert column types.

    Raises FileNotFoundError or ValueError on failure.
    """
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Transactions file not found: {path}")
    except pd.errors.ParserError as error:
        raise ValueError(f"Error parsing CSV {path}: {error}")

    df.columns = df.columns.str.strip()

    required_columns = ["Date", "Type", "Security", "Shares", "Quote", "Net Transaction Value"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {', '.join(missing)}")

    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Shares", "Quote", "Net Transaction Value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Optional column: Accrued Interest (for bonds)
    if "Accrued Interest" not in df.columns:
        df["Accrued Interest"] = 0.0
    else:
        df["Accrued Interest"] = pd.to_numeric(df["Accrued Interest"], errors="coerce").fillna(0)

    return df
