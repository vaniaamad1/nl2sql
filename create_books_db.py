import sqlite3
import pandas as pd

# 1. Read in the CSV
books_df = pd.read_csv('books.csv')

# 2. Connect (or create) the books.db database
conn = sqlite3.connect('books.db')

# 3. Write the DataFrame into a table named 'BOOKS'
books_df.to_sql('BOOKS', conn, if_exists='replace', index=False)

conn.close()
print("books.db created with table 'BOOKS'.")
