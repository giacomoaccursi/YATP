"""Caricamento dati: configurazione e transazioni."""

import pandas as pd
import json
import sys


def load_config(path):
    """Carica il file di configurazione JSON."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File di configurazione non trovato: {path}")
        sys.exit(1)
    except json.JSONDecodeError as error:
        print(f"❌ Errore nel parsing di {path}: {error}")
        sys.exit(1)


def load_transactions(path):
    """Legge il CSV delle transazioni e converte i tipi delle colonne."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"❌ File transazioni non trovato: {path}")
        sys.exit(1)
    except pd.errors.ParserError as error:
        print(f"❌ Errore nel parsing del CSV {path}: {error}")
        sys.exit(1)

    df.columns = df.columns.str.strip()

    required_columns = ["Date", "Type", "Security", "Shares", "Quote", "Net Transaction Value"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"❌ Colonne mancanti nel CSV: {', '.join(missing)}")
        sys.exit(1)

    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Shares", "Quote", "Net Transaction Value"]:
        df[col] = pd.to_numeric(df[col])
    return df
