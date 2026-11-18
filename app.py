"""Streamlit demo: Bare Necessities shipping-emissions calculator.

Run:  streamlit run app.py
"""
import pandas as pd
import streamlit as st

from emissions import calculate, load_factors, summarise

st.set_page_config(page_title="Shipping emissions calculator", layout="wide")
st.title("Shipping emissions calculator")
st.caption(
    "Distance-based method (GHG Protocol): weight x distance x emission factor, plus last mile. "
    "Demo data is SYNTHETIC. Road and last-mile factors: Smart Freight Centre India (2025). "
    "Air: UK Defra conversion factors 2025. See the sidebar for every source and assumption."
)

uploaded = st.file_uploader(
    "Upload an order file (columns: order_id, city, channel, product_weight_kg, mode)", type="csv"
)
orders = pd.read_csv(uploaded) if uploaded else pd.read_csv("data/synthetic_orders.csv")
st.write(f"**{len(orders):,} orders loaded** ({'uploaded file' if uploaded else 'synthetic demo data'})")

factors = load_factors()
with st.sidebar:
    st.header("Central-case assumptions")
    for p in ["road_ef", "air_ef", "last_mile_ef", "last_mile_km", "packaging_kg"]:
        row = factors.loc[p]
        lo, hi = float(row["low"]), float(row["high"])
        if lo == hi:
            st.write(f"{p}: {row['central']} {row['unit']} (fixed)")
            continue
        factors.loc[p, "central"] = st.slider(f"{p} ({row['unit']})", lo, hi, float(row["central"]))
    with st.expander("Sources and status of every factor"):
        st.dataframe(factors[["central", "unit", "status", "source", "note"]])
    st.caption("Low and high scenarios use the bounds in data/emission_factors.csv.")

summary = summarise(orders, factors)
c = summary.set_index("scenario")
col1, col2, col3 = st.columns(3)
col1.metric("Total (central)", f"{c.loc['central', 'total_t_co2e']:.2f} t CO2e",
            help=f"Range {c.loc['low', 'total_t_co2e']:.2f} to {c.loc['high', 'total_t_co2e']:.2f} t")
col2.metric("Average per order", f"{c.loc['central', 'avg_g_co2e_per_order']:.0f} g CO2e",
            help=f"Range {c.loc['low', 'avg_g_co2e_per_order']:.0f} to {c.loc['high', 'avg_g_co2e_per_order']:.0f} g")
col3.metric("Air share of emissions", f"{c.loc['central', 'air_share_of_emissions']:.0%}")

res = calculate(orders, factors, "central")

left, right = st.columns(2)
with left:
    st.subheader("Emissions by destination city (kg CO2e)")
    st.bar_chart(res.groupby("city")["kg_co2e_total"].sum().sort_values(ascending=False))
with right:
    st.subheader("By channel and mode")
    st.dataframe(
        res.groupby(["channel", "mode"])["kg_co2e_total"]
        .agg(orders="count", total_kg="sum", avg_kg="mean").round(3)
    )

st.subheader("Per-order line for the donation page")
pick = st.selectbox("Pick an order", res["order_id"].head(200))
o = res.set_index("order_id").loc[pick]
st.info(
    f"Your order to {o['city']} ({o['mode']}) produced about **{o['kg_co2e_total'] * 1000:.0f} g CO2e** "
    f"in delivery. A contribution to Maruvan helps grow the Bare Patch."
)

st.subheader("Scenario summary")
st.dataframe(summary.round(3), hide_index=True)
st.download_button("Download per-order results (CSV)", res.to_csv(index=False), "emissions_results.csv")
