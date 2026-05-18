---
permalink: /guides/retail
layout: default
title: Simulating Retail Sales
parent: Guides & Tutorials
nav_order: 1
---

# Simulating Retail Sales

This guide walks you through creating a realistic retail dataset.

## The Requirements

- **Time Range**: 1 year of daily data.
- **Dimensions**: `store_id`, `product_category`.
- **Metrics**: `revenue`.
- **Behaviors**:
    - Weekly seasonality (more sales on weekends).
    - Yearly growth (upward trend).
    - Holiday spikes (Black Friday, Christmas).
    - Random "Stockout" events (Missing data).

---

## The Solution (CLI)

```bash
tsdata generate \
    --start 2023-01-01 --end 2023-12-31 --granularity D \
    --dims "store_id:auto_generate_name:STORE_" \
    --dims "product_category:Electronics,Apparel,Home" \
    --mets "revenue:LinearTrend(offset=1000,limit=1500)+SinusoidalTrend(amplitude=200,freq=7)+HolidayTrend(country=US,effect=500)" \
    --anomalies "revenue:MissingData(mode=burst,probability=0.01,max_length=3)" \
    --output retail_data.csv
```

## Key Takeaways

1. **Composition**: Notice how we added `LinearTrend`, `SinusoidalTrend`, and `HolidayTrend` to create the `revenue` metric.
2. **Frequency**: Since our granularity is `D` (daily), `freq=7` in `SinusoidalTrend` naturally creates a weekly pattern.
3. **Anomalies**: `MissingData` with `mode=burst` simulates a store being closed or running out of stock for a few days.
