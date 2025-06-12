# app.py

import os
import re
import html

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

import google.generativeai as genai
from dotenv import load_dotenv

from core import COMBINED_PROMPT, transcribe, run_sql

# STEP 1 – load your Gemini API key
load_dotenv()
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    st.error("GENAI_API_KEY not found. Please set it in .env")
else:
    genai.configure(api_key=api_key)

# 2. Streamlit UI setup
st.set_page_config(page_title="Crypto NL→SQL + Charts", layout="centered")
st.title("💰 Query & Chart Crypto Prices by Plain English")

st.markdown(
    """
Type your question in plain English (e.g. “plot BTC high over 2021”),  
-or- upload a short audio clip (WAV/MP3) of you asking it.  
The app will generate SQL, show results, and plot if requested.
"""
)

# INPUT: text or audio upload
q_text = st.text_input("Type your question here:")
audio_file = st.file_uploader("—or upload a .wav/.mp3 file—", type=["wav", "mp3"])

question = None
if q_text:
    question = q_text
elif audio_file:
    with st.spinner("Transcribing…"):
        # read raw bytes and pass to your existing transcribe()
        question = transcribe(audio_file.read())
        st.success(f"Transcript: {question}")

# ASK button
if st.button("Ask"):
    if not question:
        st.warning("Please either type a question or upload an audio clip.")
    else:
        # 1) Generate SQL via Gemini
        model = genai.GenerativeModel("models/gemini-1.5-flash-001")
        response = model.generate_content([COMBINED_PROMPT, question])
        sql = response.text.strip()

        # 2) Strip fences + normalize ORDER BY + patch schema.table
        sql = re.sub(r"^```.*\n", "", sql)
        sql = re.sub(r"\n```$", "", sql)
        order_patterns = re.compile(r"(?i)ORDER BY\s+[^;]+", flags=re.MULTILINE)
        all_orders = order_patterns.findall(sql)
        if all_orders:
            last_order = all_orders[-1].strip()
            sql = order_patterns.sub("", sql).strip().rstrip(";")
            sql = sql + "\n" + last_order
        alias_to_table = {
            "coin_bitcoin": "BITCOIN",
            "coin_chainlink": "CHAINLINK",
            "coin_ethereum": "ETHEREUM",
            "coin_usdcoin": "USDCOIN",
        }
        for alias, tbl in alias_to_table.items():
            sql = re.sub(fr"(?i)\bFROM\s+{alias}\b(?!\.)", f"FROM {alias}.{tbl}", sql)
            sql = re.sub(fr"(?i)\bJOIN\s+{alias}\b(?!\.)", f"JOIN {alias}.{tbl}", sql)

        st.subheader("🔧 Generated SQL")
        st.code(sql, language="sql")

        # 3) Execute & show results
        try:
            rows, cols = run_sql(sql)
            cleaned = [
                tuple(html.unescape(cell) if isinstance(cell, str) else cell for cell in row)
                for row in rows
            ]
            df = pd.DataFrame(cleaned, columns=cols)
            st.subheader("📊 Results")
            st.dataframe(df)

            # 3.1) Re-run for plotting
            rows2, cols2 = run_sql(sql)
            df_plot = pd.DataFrame(rows2, columns=cols2)

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
                        df_plot['Date'] = pd.to_datetime(df_plot['Date'], errors='coerce')
                        df_plot = df_plot.dropna(subset=['Date'])
                        for src in df_plot['Source'].unique():
                            sub = df_plot[df_plot['Source']==src]
                            ycol = num_cols[0] if num_cols else 'Close'
                            ax.plot(sub['Date'], sub[ycol], label=src)
                        ax.set_xlabel('Date'); ax.set_ylabel(ycol)
                        ax.legend(); ax.set_title(f"Line Chart of {ycol} over Time")
                    else:
                        st.warning("No 'Date' column for line chart.")

                plt.tight_layout()
                st.pyplot(fig)

        except Exception as e:
            st.error(f"SQL Error: {e}")
