import pandas as pd
import sqlite3

# 1) Load the “raw” CSV you just saved. 
#
#    Because the very first column is just an unnamed index (0,1,2…), 
#    pandas will read it as a “Unnamed: 0” column by default. 
#    We’ll drop that after loading.
tv_df = pd.read_csv('tv_shows.csv')

# 2) Rename columns to remove the leading comma. 
#    The file’s header is ["", "title", "year", …], 
#    so pandas calls the first column "Unnamed: 0". We don’t need it.
tv_df = tv_df.drop(columns=[tv_df.columns[0]])  # drop that unnamed index
tv_df.columns = ['Title', 'Year', 'Runtime', 'Rating', 'Votes', 'Genre', 'Description']

# 3) (Optional) Clean up any stray quotes, NaNs, etc.
#    For example, if “Votes” came in as a string like "748,557", remove commas and convert to int:
tv_df['Votes'] = (
    tv_df['Votes']
    .astype(str)
    .str.replace(',', '', regex=False)
    .replace({r'^\s*$': None}, regex=True)
    .astype('Int64')  # allow for missing values
)

#    Also strip any leading/trailing whitespace on text fields:
tv_df['Title']       = tv_df['Title'].astype(str).str.strip()
tv_df['Genre']       = tv_df['Genre'].astype(str).str.strip()
tv_df['Description'] = tv_df['Description'].astype(str).str.strip()

# 4) Save a clean CSV (so you can eyeball it later if you want)
tv_df.to_csv('tvshows_clean.csv', index=False)
print(f"tvshows_clean.csv written ({len(tv_df)} rows).")

# 5) Write to SQLite. We’ll create (or replace) tvshows.db with a table named TVSHOWS.
conn = sqlite3.connect('tvshows.db')
tv_df.to_sql('TVSHOWS', conn, if_exists='replace', index=False)

# 6) (Optional) Add a simple PRIMARY KEY on rowid by creating a new table:
#    – SQLite doesn’t let us ALTER an existing table to add PK easily,
#      but we can create a fresh table with INTEGER PRIMARY KEY if you need it.
conn.execute("""
    CREATE TABLE IF NOT EXISTS TVSHOWS_with_id AS
    SELECT ROWID      AS id,
           Title      AS Title,
           Year       AS Year,
           Runtime    AS Runtime,
           Rating     AS Rating,
           Votes      AS Votes,
           Genre      AS Genre,
           Description AS Description
    FROM TVSHOWS;
""")
conn.execute("DROP TABLE TVSHOWS;")
conn.execute("ALTER TABLE TVSHOWS_with_id RENAME TO TVSHOWS;")

conn.commit()
conn.close()
print("tvshows.db created (table = TVSHOWS with columns: id, Title, Year, Runtime, Rating, Votes, Genre, Description).")
