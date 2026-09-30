# Project structure

```
├── dashboard.html          # Command-center UI — single page, no build step
│                           #   • sticky nav (Overview / Signal Control / Analytics / Environment / About)
│                           #   • live city map (canvas) with click-to-open junction selection
│                           #   • per-junction digital-twin signal simulation
│                           #   • prediction cards, forecast, sensors, environmental estimates
├── server.py               # FastAPI backend — decision engine
│                           #   • /api/decision: per-junction signal plan, RF predictions,
│                           #     30-min forecast, simulated sensors, environmental estimate
│                           #   • /api/health: service + model status
├── train_model.py          # Trains the congestion classifier and demand forecaster
├── models/                 # Trained models (joblib) + training metrics
│   ├── congestion_model.joblib
│   ├── traffic_forecaster.joblib
│   └── *.json              # metrics
├── data/
│   └── synthetic_traffic_data.csv   # Synthetic benchmark dataset
├── docs/screenshots/       # README images
├── requirements.txt        # Python dependencies
├── Procfile / render.yaml  # Deployment configs (Render)
└── run_dashboard.bat       # One-click local start (Windows)
```

## Signal optimizer guarantees

Every adaptive green split produced by the engine (backend or embedded
fallback):

- bounded to **20–90 s per phase**
- sums to **exactly 180 s** per cycle
- demand-weighted via a water-fill allocation with integer repair

## Simulation model

Each junction runs two parallel discrete-event simulations with identical
Poisson arrivals: a fixed-time baseline (60/60/60) and the AI adaptive plan.
Vehicle motion uses car-following dynamics; the comparison yields queue
lengths, delay, throughput and idle exposure, which drive the environmental
estimates through explicit idle-emission factors.

## Notes

Training data is synthetic; the traffic stream is simulated and not connected
to real infrastructure. See the Notes & limitations section of the README.
