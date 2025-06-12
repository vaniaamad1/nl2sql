import pandas as pd

# 1. Scrape Wikipedia’s "Highest-grossing superhero films" table
url = 'https://en.wikipedia.org/wiki/List_of_highest-grossing_superhero_films'
df_list = pd.read_html(url)

# 2. Take only the first table (top 50 movies)
movies_df = df_list[0].copy().drop(['Ref', 'Superhero(es)', 'Rank'], axis=1)

# 3. Clean up the "Worldwide gross" column (remove $ and commas, convert to int, then to millions)
movies_df['Worldwide gross'] = (
    movies_df['Worldwide gross']
    .apply(lambda x: x.replace('$', '').replace(',', '').replace(' ', ''))
    .astype(int) / 1_000_000
).round(2)

# 4. Rename columns for simplicity
movies_df.columns = ['Name', 'Revenue', 'Year', 'Universe']

# 5. Keep only the top 50 rows (already ordered that way)
movies_df = movies_df.head(50)

# 6. Save to CSV
movies_df.to_csv('Movie.csv', index=False)

print("Movie.csv created with", movies_df.shape[0], "rows.")
