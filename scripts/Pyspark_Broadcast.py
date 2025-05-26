import pandas as pd

invalid = []
for row in rows:
    if row['email'] is None:
        invalid.append(row)


df = pd.read_parquet("…")
invalid = df[df.email.isna()]



