import os
import re
import sqlite3
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from audiorecorder import audiorecorder
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
import html
import pandas as pd
import matplotlib.pyplot as plt

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

# 3. Streamlit UI setup
st.set_page_config(page_title="Crypto NL→SQL + Charts", layout="centered")
st.title("💰 Query & Chart Crypto Prices by Plain English")

st.markdown(
    """
Type your question in plain English (e.g. “plot BTC high over 2021”),  
or hold to record (3–8 seconds). The app will query the coin tables and,  
if you ask for a graph, it will generate & display it.
"""
)

# Text vs. voice input
q_text = st.text_input("Type your question here:")
audio = audiorecorder("Hold to record", "Release to stop")

# Determine source of question
question = None
if q_text and not audio:
    question = q_text
elif audio and not q_text:
    with st.spinner("Transcribing…"):
        question = transcribe(audio)
        st.success(f"Transcript: {question}")
elif q_text and audio:
    st.info("Using typed question.")
    question = q_text

# Single Ask button
if st.button("Ask", key="ask_button"):
    if not question:
        st.warning("Please type or speak your question (but not both).")
    else:
        # 1) Generate SQL via Gemini
        model = genai.GenerativeModel("models/gemini-1.5-flash-001")
        response = model.generate_content([COMBINED_PROMPT, question])
        sql = response.text.strip()

        # 2) Strip fences
        sql = re.sub(r"^```.*\n", "", sql)
        sql = re.sub(r"\n```$", "", sql)

        # 2.5) Normalize ORDER BY clauses
        order_patterns = re.compile(r"(?i)ORDER BY\s+[^;]+", flags=re.MULTILINE)
        all_orders = order_patterns.findall(sql)
        if all_orders:
            last_order = all_orders[-1].strip()
            sql = order_patterns.sub("", sql).strip().rstrip(";")
            sql = sql + "\n" + last_order

        # 2.6) Patch missing schema.table references
        alias_to_table = {
            "coin_bitcoin": "BITCOIN",
            "coin_chainlink": "CHAINLINK",
            "coin_ethereum": "ETHEREUM",
            "coin_usdcoin": "USDCOIN",
        }
        for alias, tbl in alias_to_table.items():
            sql = re.sub(
                fr"(?i)\bFROM\s+{alias}\b(?!\.)",
                f"FROM {alias}.{tbl}",
                sql
            )
            sql = re.sub(
                fr"(?i)\bJOIN\s+{alias}\b(?!\.)",
                f"JOIN {alias}.{tbl}",
                sql
            )

        st.subheader("🔧 Generated SQL")
        st.code(sql, language="sql")

        # 3) Execute and display full results
        try:
            rows, cols = run_sql(sql)
            cleaned = [
                tuple(html.unescape(cell) if isinstance(cell, str) else cell for cell in row)
                for row in rows
            ]
            df = pd.DataFrame(cleaned, columns=cols)
            st.subheader("📊 Results")
            st.dataframe(df)

            # 3.1) Re-run SQL for plotting
            rows_plot, cols_plot = run_sql(sql)
            df_plot = pd.DataFrame(rows_plot, columns=cols_plot)

            # 4) Plot if requested
            plot_kw = ["plot","graph","chart","visualize","line","bar","histogram","pie"]
            if any(kw in question.lower() for kw in plot_kw):
                st.subheader("📈 Chart")
                fig, ax = plt.subplots()
                ql = question.lower()
                num_cols = df_plot.select_dtypes(include="number").columns.tolist()
                cat_cols = [c for c in df_plot.columns if c not in num_cols]

                if "pie" in ql and num_cols and cat_cols:
                    ax.pie(df_plot[num_cols[0]], labels=df_plot[cat_cols[0]], autopct='%1.1f%%')
                    ax.set_title(f"Pie Chart of {num_cols[0]} by {cat_cols[0]}")
                elif "hist" in ql:
                    if num_cols:
                        ax.hist(df_plot[num_cols[0]].dropna())
                        ax.set_xlabel(num_cols[0]); ax.set_ylabel("Frequency")
                        ax.set_title(f"Histogram of {num_cols[0]}")
                    else:
                        st.warning("No numeric column available for histogram.")
                elif "bar" in ql:
                    if num_cols:
                        grp = "Source" if "Source" in df_plot.columns else cat_cols[0]
                        df_plot.groupby(grp)[num_cols[0]].sum().plot.bar(ax=ax)
                        ax.set_xlabel(grp); ax.set_ylabel(num_cols[0])
                        ax.set_title(f"Bar Chart of {num_cols[0]} by {grp}")
                    else:
                        st.warning("No numeric column available for bar chart.")
                else:
                    if 'Date' in df_plot.columns:
                        df_plot['Date']=pd.to_datetime(df_plot['Date'],errors='coerce')
                        df_plot=df_plot.dropna(subset=['Date'])
                        for src in df_plot['Source'].unique():
                            sub=df_plot[df_plot['Source']==src]
                            ycol=num_cols[0] if num_cols else 'Close'
                            ax.plot(sub['Date'],sub[ycol],label=src)
                        ax.set_xlabel('Date'); ax.set_ylabel(num_cols[0] if num_cols else 'Close')
                        ax.legend(); ax.set_title(f"Line Chart of {num_cols[0] if num_cols else 'Close'} over Time")
                    else:
                        st.warning("No 'Date' column for line chart.")

                plt.tight_layout()
                st.pyplot(fig)

        except Exception as e:
            st.error(f"SQL Error: {e}")
