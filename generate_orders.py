"""Generate a SYNTHETIC order file for demoing the shipping-emissions calculator.

Every number here is made up. It only exists so the calculator can be demonstrated
before real order data is available. Replace with a real export when you have one.

Usage:  python generate_orders.py --n 5000 --out data/synthetic_orders.csv
"""
import argparse

import numpy as np
import pandas as pd

from emissions import ORIGIN, haversine_km


def generate(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cities = pd.read_csv("data/cities.csv")
    cities["order_share"] /= cities["order_share"].sum()

    idx = rng.choice(len(cities), size=n, p=cities["order_share"])
    df = cities.iloc[idx].reset_index(drop=True)[["city", "state", "lat", "lon", "airport_km_dest"]]
    df.insert(0, "order_id", [f"SYN-{i:05d}" for i in range(1, n + 1)])

    # Channel mix (made up): mostly website orders, some bulk gifting
    df["channel"] = rng.choice(["website", "corporate_gifting"], size=n, p=[0.92, 0.08])

    # Product weight in kg: small personal-care parcels, heavier gifting boxes
    web_w = rng.lognormal(mean=np.log(0.45), sigma=0.5, size=n)
    gift_w = rng.lognormal(mean=np.log(8.0), sigma=0.6, size=n)
    df["product_weight_kg"] = np.where(df["channel"] == "website", web_w, gift_w).round(3)

    # Mode: air more likely for far destinations and some express orders (made up)
    dist = haversine_km(ORIGIN[0], ORIGIN[1], df["lat"], df["lon"])
    p_air = np.clip(0.05 + dist / 4000, 0, 0.6)
    p_air[df["airport_km_dest"].isna().to_numpy()] = 0.0  # no airport leg defined = road only
    p_air[(df["channel"] == "corporate_gifting").to_numpy()] = 0.0  # bulk gifting boxes go by surface (assumption)
    df["mode"] = np.where(rng.random(n) < p_air, "air", "surface")

    return df.drop(columns=["lat", "lon", "airport_km_dest"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--out", default="data/synthetic_orders.csv")
    args = ap.parse_args()
    out = generate(args.n)
    out.to_csv(args.out, index=False)
    print(f"Wrote {len(out)} synthetic orders to {args.out}")
