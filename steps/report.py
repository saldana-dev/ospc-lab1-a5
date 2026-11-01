"""Revenue by region and month (revenue_by_region_month.csv)."""

#fix written with the help of Claude 

import os

import pandas as pd

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

COLUMNS = ["order_date", "region", "quantity", "unit_price"]
CHUNK = 1_000_000

revenue = None
n_orders = 0
for chunk in pd.read_csv(DATA, usecols=COLUMNS, chunksize=CHUNK):
    n_orders += len(chunk)
    value = chunk["quantity"] * chunk["unit_price"]
    month = pd.to_datetime(chunk["order_date"]).dt.month.rename("order_date")
    part = value.groupby([chunk["region"], month]).sum()
    revenue = part if revenue is None else revenue.add(part, fill_value=0)

print(f"report: loaded {n_orders:,} orders in chunks of {CHUNK:,}", flush=True)

table = revenue.unstack()
table.round(2).to_csv(os.path.join(OUT, "revenue_by_region_month.csv"))
print("report: done")