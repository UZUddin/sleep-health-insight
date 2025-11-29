Project Overview
Web-based dashboard that integrates sleep data exported from consumer health apps (e.g., Apple Health, Fitbit) and provides data-driven insights into a user’s sleep quality.
It will analyze multiple physiological, behavioral, and environmental metrics to identify patterns and anomalies affecting sleep health.
Process XML (or JSON) exports from Apple Health and similar apps.
Detect available metrics automatically and adjust computation to optimize for limited data (reduce load when not all metrics are present).
Input Metrics: (need 4-5)
Demographics: Gender, Height, Weight
Sleep Data: Total sleep time, REM vs. non-REM
Vitals: Heart rate, HRV, respiratory rate
Activity: Movement index, device usage
Environment: Sound levels, snoring detection, CO₂ (if available)
Output Metrics: (three categories) 
Activity (movement, device usage, sleep duration)
Vitals (heart rate, variability, respiratory rate)
Environment (sound levels, snoring, CO₂, temperature if available)
Summarized analysis and visualizations of sleep performance vs. personal or population averages.
(Optional) AI model to predict poor sleep nights based on recent trends.
