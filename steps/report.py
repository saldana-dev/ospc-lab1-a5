"""Revenue by region and month (revenue_by_region_month.csv)."""

import os
import pandas as pd

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

# Read only the columns we need and compute revenue directly
orders = pd.read_csv(DATA, usecols=["order_date", "region", "quantity", "unit_price"])
orders['revenue'] = orders['quantity'] * orders['unit_price']
orders['month'] = pd.to_datetime(orders['order_date']).dt.to_period('M')

# Group and sum - this is memory efficient
revenue = orders.groupby(['region', 'month'])['revenue'].sum().reset_index()
revenue['month'] = revenue['month'].astype(str)

revenue.to_csv(os.path.join(OUT, "revenue_by_region_month.csv"), index=False)
print("report: done")
