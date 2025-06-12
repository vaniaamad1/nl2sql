import sqlite3
import pandas as pd

# 1. Read Movie.csv (which you just generated)
movies_df = pd.read_csv('Movie.csv')

# 2. Connect (or create) the SQLite database file named movie.db
conn = sqlite3.connect('movie.db')

# 3. Write the DataFrame to a table named "Movie"
movies_df.to_sql('Movie', conn, if_exists='replace', index=False)

# 4. Clean up
conn.close()
print("movie.db created with table 'Movie'.")
