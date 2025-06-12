
# app.py (using ipywidgets)

from ipywidgets import Text, Button, Output, VBox, HBox
from IPython.display import display, clear_output
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai
import core
from core import COMBINED_PROMPT, run_sql, transcribe


# Input widgets
question_input = Text(description="Question:")
ask_button = Button(description="Ask")
results_out = Output()
plot_out = Output()

# Callback
def on_ask_clicked(_):
    q = question_input.value.strip()
    with results_out:
        clear_output()
        if not q:
            print("Please enter a question.")
            return
        # Generate SQL
        sql = core.generate_sql(q)
        print("🔧 Generated SQL:")
        print(sql)
        # Execute
        df = core.run_sql(sql)
        display(df)
    with plot_out:
        clear_output()
        # Re-run for plotting
        df_plot = core.run_sql(sql)
        if any(kw in q.lower() for kw in ["plot","graph","chart","visualize","line","bar","histogram","pie"]):
            fig, ax = plt.subplots()
            numeric_cols = df_plot.select_dtypes(include="number").columns.tolist()
            categorical_cols = [c for c in df_plot.columns if c not in numeric_cols]
            ql = q.lower()
            if "pie" in ql and numeric_cols and categorical_cols:
                ax.pie(df_plot[numeric_cols[0]], labels=df_plot[categorical_cols[0]], autopct='%1.1f%%')
                ax.set_title(f"Pie Chart of {numeric_cols[0]} by {categorical_cols[0]}")
            elif "hist" in ql:
                ax.hist(df_plot[numeric_cols[0]].dropna())
                ax.set_xlabel(numeric_cols[0]); ax.set_ylabel("Frequency")
                ax.set_title(f"Histogram of {numeric_cols[0]}")
            elif "bar" in ql:
                grp = "Source" if "Source" in df_plot.columns else categorical_cols[0]
                df_plot.groupby(grp)[numeric_cols[0]].sum().plot.bar(ax=ax)
                ax.set_xlabel(grp); ax.set_ylabel(numeric_cols[0])
                ax.set_title(f"Bar Chart of {numeric_cols[0]} by {grp}")
            else:
                if 'Date' in df_plot.columns:
                    df_plot['Date'] = pd.to_datetime(df_plot['Date'], errors='coerce')
                    df_plot = df_plot.dropna(subset=['Date'])
                    for src, subset in df_plot.groupby('Source'):
                        ax.plot(subset['Date'], subset[numeric_cols[0] if numeric_cols else 'Close'], label=src)
                    ax.set_xlabel('Date'); ax.set_ylabel(numeric_cols[0] if numeric_cols else 'Close')
                    ax.legend(); ax.set_title(f"Line Chart of {numeric_cols[0] if numeric_cols else 'Close'} over Time")
            plt.tight_layout()
            display(fig)

ask_button.on_click(on_ask_clicked)

# Layout
display(VBox([HBox([question_input, ask_button]), results_out, plot_out]))
