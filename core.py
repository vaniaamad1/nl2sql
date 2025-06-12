# core.py

import os
import re
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
from pydub import AudioSegment
from io import BytesIO
import speech_recognition as sr
import pandas as pd


# STEP 1 - load the key from .env
load_dotenv()
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    st.error("GENAI_API_KEY not found. Please set it in .env")
else:
    genai.configure(api_key=api_key)

# 2. Combined prompt- change when change db
COMBINED_PROMPT = """
You are an expert in converting English questions to SQL queries.
You have four attached SQLite tables:

  ATTACH DATABASE 'bitcoin.db'   AS coin_bitcoin;
  ATTACH DATABASE 'chainlink.db' AS coin_chainlink;
  ATTACH DATABASE 'ethereum.db'  AS coin_ethereum;
  ATTACH DATABASE 'usdcoin.db'   AS coin_usdcoin;

Each table has columns: SNo, Name, Symbol, Date, High, Low, Open, Close, Volume, Marketcap.
When querying across them, you may query any single table or UNION ALL across multiple tables.
Prefix each SELECT with a literal 'Source' column indicating which coin.

Do NOT wrap your answer in backticks or include the word “SQL.”

Example:
  SELECT 'Bitcoin'  AS Source, Date, Close
    FROM coin_bitcoin.BITCOIN
   WHERE Symbol='BTC'
  UNION ALL
  SELECT 'Ethereum' AS Source, Date, Close
    FROM coin_ethereum.ETHEREUM
   WHERE Symbol='ETH';

ALSO whenver a date is asked, remeber that the date column has date followed with 23::59:59 for all entries

make sure to remeber that after the sql part the user will also make a graph from the data, so if u think the date or any other 
feature should be added to the sql query add it for the graph to be made better

"""


def transcribe(audio_input) -> str:
    """Convert audio_input (AudioSegment or bytes) into text via Google Web Speech."""
    if isinstance(audio_input, AudioSegment):
        wav = BytesIO()
        audio_input.export(wav, "wav")
        wav.seek(0)
    elif isinstance(audio_input, (bytes, bytearray)):
        wav = BytesIO(audio_input)
    else:
        raise RuntimeError("Unsupported audio input type.")
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav) as source:
        audio_data = recognizer.record(source)
    return recognizer.recognize_google(audio_data)


def run_sql(sql: str):
    """Attach all coin DBs in-memory and execute the given SQL."""
    conn = sqlite3.connect(":memory:")
    cwd = os.getcwd()
    conn.execute(f"ATTACH DATABASE '{cwd}/bitcoin.db'   AS coin_bitcoin;")
    conn.execute(f"ATTACH DATABASE '{cwd}/chainlink.db' AS coin_chainlink;")
    conn.execute(f"ATTACH DATABASE '{cwd}/ethereum.db'  AS coin_ethereum;")
    conn.execute(f"ATTACH DATABASE '{cwd}/usdcoin.db'   AS coin_usdcoin;")
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return rows, cols