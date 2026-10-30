"""Number of orders per region, quarter and order size (segments.csv)."""

import os
import pandas as pd

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

orders = pd.read_csv(DATA, usecols=["order_date", "region", "quantity", "unit_price"])

orders['order_date'] = pd.to_datetime(orders['order_date'])
orders['quarter'] = (orders['order_date'].dt.month - 1) // 3 + 1
orders['value'] = orders['quantity'] * orders['unit_price']

def classify_size(value):
    if value >= 500:
        return 'large'
    elif value >= 100:
        return 'medium'
    else:
        return 'small'

orders['size'] = orders['value'].apply(classify_size)
orders['segment'] = 'Q' + orders['quarter'].astype(str) + ' ' + orders['size']

counts = orders.groupby(['region', 'segment']).size().unstack(fill_value=0)
counts.to_csv(os.path.join(OUT, "segments.csv"))
print("segments: done")
