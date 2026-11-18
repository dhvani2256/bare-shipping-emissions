# Shipping emissions calculator (Bare Necessities demo)

Estimates CO2e from delivering orders out of Bengaluru, using the GHG Protocol
distance-based method:

    emissions = (product + packaging weight, t) x distance (km) x emission factor (kg CO2e/t-km)
                + last-mile emission per parcel

Every result is given as low / central / high.

## Run it

    pip install pandas numpy streamlit
    python generate_orders.py --n 5000      # makes data/synthetic_orders.csv
    python emissions.py                     # prints the summary in the terminal
    streamlit run app.py                    # opens the interactive demo

## Run it in Jupyter

Open `shipping_emissions.ipynb` from inside this folder and run the cells top to bottom.

## Files

| File | What it does |
|---|---|
| data/cities.csv | Destination cities, coordinates, made-up order shares, Google Maps driving distance (road_km) and airport-to-centre distance (airport_km_dest) |
| data/emission_factors.csv | Every assumption, with low/central/high and a note |
| generate_orders.py | Creates SYNTHETIC demo orders |
| emissions.py | The calculator (distance, emissions, scenarios) |
| app.py | Streamlit demo with upload, sliders, charts, per-order line |
| shipping_emissions.ipynb | Jupyter notebook version: factors, results, chart, road vs air example |

## Emission factors

Every factor in data/emission_factors.csv has a `status`:

- SOURCED: road and last-mile values from Smart Freight Centre India, India Default GHG
  Emission Values v1.2 (May 2025), road table p.5 (well-to-wheel, kg CO2e per tonne-km).
- SOURCED (VERIFIED): air values from the official Defra 2025 conversion factors
  (Freighting goods tab, rows 98-99; WTT- delivery vehs & freight tab, rows 92-93).
- MEASURED: Google Maps driving distances and airport legs (collected 2026-11-18).
- ASSUMPTION / ESTIMATE: last-mile distance and packaging weight.

All factors are on a well-to-wheel basis (fuel production + combustion).

## Before showing this to anyone

1. Weigh a real Bare parcel box and update packaging_kg.
2. Optional: switch from city to pincode lookup using the India Post pincode directory.
3. Keep the label "synthetic demo data" visible wherever results appear.

## Order file format (for real data)

    order_id, city, channel, product_weight_kg, mode
    BN-1001, Mumbai, website, 0.42, surface

`mode` is `surface` or `air`. Cities must exist in data/cities.csv (or extend that file).
