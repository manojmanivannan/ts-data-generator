---
layout: default
title: Core Concepts
permalink: /concepts
nav_order: 3
has_children: true
---

# Core Concepts

Understanding the building blocks of the Synthetic Time Series Data Generator.

The library is built around three primary primitives that work together to create realistic datasets:

## 1. Dimensions
Categorical or continuous labels that define the "context" of your data (e.g., `region`, `device_id`, `user_type`). These are generated using infinite iterators.

[Explore Dimension Generators]({{ site.baseurl }}/dimensions){: .btn .btn-outline }

## 2. Metrics (Trends)
The numeric values you want to simulate. Metrics are composed of one or more **Trends** (e.g., a Linear ramp + Sine wave + AR Noise).

[Explore Trend Functions]({{ site.baseurl }}/trends){: .btn .btn-outline }

## 3. Anomalies
Injectable irregularities that are applied *after* the base metric is generated. This allows you to simulate real-world failures without changing the underlying trend logic.

[Explore Anomaly Injection]({{ site.baseurl }}/anomalies){: .btn .btn-outline }
