"""Core shipping-emissions calculator (distance-based method, GHG Protocol).

Emissions per parcel = weight (t) x distance (km) x emission factor (kg CO2e / t-km)
                       for each leg (line-haul road or air, plus last-mile van),
                       allocated by tonne-km as in the GLEC Framework.

Surface parcels: one road leg, Bengaluru -> destination.
Air parcels:     road to airport + flight + road from airport.

All factors live in data/emission_factors.csv with low / central / high values,
so every result comes with a range.
"""
import numpy as np
import pandas as pd

ORIGIN = (12.9716, 77.5946)  # Bengaluru (Bare HQ is in central Bengaluru)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle (straight-line) distance in km. Works on scalars or arrays."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def load_factors(path: str = "data/emission_factors.csv") -> pd.DataFrame:
    return pd.read_csv(path).set_index("parameter")


def attach_coordinates(orders: pd.DataFrame, cities_path: str = "data/cities.csv") -> pd.DataFrame:
    """Add lat/lon by city name. Swap this for a pincode lookup once you have
    the India Post pincode directory (join on pincode instead of city)."""
    cities = pd.read_csv(cities_path)
    cols = [c for c in ["city", "lat", "lon", "road_km", "airport_km_dest"] if c in cities]
    cities = cities[cols]
    out = orders.merge(cities, on="city", how="left")
    missing = out["lat"].isna()
    if missing.any():
        raise ValueError(f"No coordinates for: {sorted(out.loc[missing, 'city'].unique())}")
    return out


def calculate(orders: pd.DataFrame, factors: pd.DataFrame, scenario: str = "central") -> pd.DataFrame:
    """Return orders with distance and emissions columns for one scenario."""
    f = factors[scenario]
    df = attach_coordinates(orders) if "lat" not in orders else orders.copy()

    gcd = haversine_km(ORIGIN[0], ORIGIN[1], df["lat"], df["lon"])
    is_air = df["mode"].str.lower().eq("air")

    # Road distance: Google Maps driving distance per city; circuity factor only as fallback
    surface_km = df["road_km"].fillna(gcd * f["road_circuity"]) if "road_km" in df else gcd * f["road_circuity"]
    if "airport_km_dest" in df:
        no_airport = is_air & df["airport_km_dest"].isna()
        if no_airport.any():
            raise ValueError(f"Air orders to cities without an airport leg: {sorted(df.loc[no_airport, 'city'].unique())}")
        dest_leg = df["airport_km_dest"].fillna(0)
    else:
        dest_leg = f["airport_km_origin"]
    road_km = np.where(is_air, f["airport_km_origin"] + dest_leg, surface_km)
    air_km = np.where(is_air, gcd * f["air_distance_uplift"], 0.0)

    weight_t = (df["product_weight_kg"] + f["packaging_kg"]) / 1000.0

    df["road_km"] = road_km.round(1)
    df["air_km"] = air_km.round(1)
    df["kg_co2e_road"] = weight_t * road_km * f["road_ef"]
    df["kg_co2e_air"] = weight_t * air_km * f["air_ef"]
    df["kg_co2e_last_mile"] = weight_t * f["last_mile_km"] * f["last_mile_ef"]
    df["kg_co2e_total"] = df[["kg_co2e_road", "kg_co2e_air", "kg_co2e_last_mile"]].sum(axis=1)
    return df


def summarise(orders: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Total and per-order emissions for low / central / high scenarios."""
    rows = []
    for s in ["low", "central", "high"]:
        r = calculate(orders, factors, s)
        rows.append({
            "scenario": s,
            "orders": len(r),
            "total_t_co2e": r["kg_co2e_total"].sum() / 1000,
            "avg_g_co2e_per_order": r["kg_co2e_total"].mean() * 1000,
            "air_share_of_emissions": r["kg_co2e_air"].sum() / r["kg_co2e_total"].sum(),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    orders = pd.read_csv("data/synthetic_orders.csv")
    factors = load_factors()
    print(summarise(orders, factors).round(3).to_string(index=False))
    res = calculate(orders, factors)
    print("\nBy channel (central):")
    print(res.groupby("channel")["kg_co2e_total"].agg(["count", "sum", "mean"]).round(3))
    print("\nTop 5 cities by total kg CO2e (central):")
    print(res.groupby("city")["kg_co2e_total"].sum().sort_values(ascending=False).head().round(1))
