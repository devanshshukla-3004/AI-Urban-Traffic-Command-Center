<div align="center">

# 🚦 AI Urban Traffic Command Center

**A decision-support dashboard that uses machine learning to cut congestion and vehicle emissions at signalized intersections.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-Random%20Forest-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Deployment](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](#-deploy-online-render--free)

*Live demo — `https://ai-urban-traffic-command-center.onrender.com/`

</div>

---

## 📸 Preview

| Overview | Live City Map |
|---|---|
| ![Overview](docs/screenshots/overview.png) | ![Live City Map](docs/screenshots/live-city-map.png) |

| Environmental Intelligence |
|---|
| ![Environment](docs/screenshots/environment.png) |

## ✨ Features

- 🗺️ **Live City Map** — an interactive network map with three junctions; roads and pins glow by live congestion level, with moving traffic dots
- 🖥️ **Digital-twin junction panel** — select any junction on the map to open its real-time signal simulation: working traffic lights, countdowns, cycle timeline, car-following physics and queue bars
- 🤖 **ML congestion prediction** — a Random Forest classifier estimates Low / Moderate / High congestion per approach with class probabilities
- ⏱️ **Adaptive signal optimizer** — allocates green time from predicted demand, always bounded to **20–90 s per phase** and an **exact 180 s cycle**
- 📈 **30-minute demand forecast** — a separate regression model projects network demand across the decision horizon
- ♻️ **Environmental intelligence** — fuel, CO₂ and PM2.5 savings estimated by comparing idle time under fixed-time vs AI plans
- 📡 **Simulated sensor network** — AQI, PM2.5 and weather feed derived from network state
- 🎛️ **Manual override** — operators can set green times by hand; the 20–90 s bounds and 180 s cycle are still enforced automatically

## 🧠 How it works

```
Approach demand (per junction)
        │
        ▼
Random Forest ──► congestion class + probabilities
        │
        ▼
Bounded optimiser ──► adaptive green split (Σ = 180 s, 20–90 s/phase)
        │
        ▼
Discrete-event simulation ──► fixed-time baseline  vs  AI plan
        │                                   (queues, delay, idle time)
        ▼
Environmental model ──► fuel / CO₂ / PM2.5 reduction estimates
```

The backend exposes one decision endpoint per junction; the frontend runs a
physics-based digital twin for every junction simultaneously and compares the
AI plan against a fixed-time baseline in real time.

## 🛠️ Tech stack

| Layer | Technology |
|---|---|
| Frontend | Single-page HTML / CSS / vanilla JS, canvas digital twins (no build step) |
| Backend | FastAPI + Uvicorn |
| Machine learning | scikit-learn Random Forest classifier + demand forecaster |
| Simulation | Discrete-event queueing with car-following vehicle dynamics |
| Deployment | Render (Docker-free, `render.yaml` + `Procfile` included) |

## 🚀 Run locally

```bash
git clone https://github.com/devanshshukla-3004/AI-Urban-Traffic-Command-Center
cd ai-traffic-command-center
pip install -r requirements.txt
python train_model.py          # optional — models are already included
uvicorn server:app --reload --port 8000
```

Open **http://127.0.0.1:8000**.

Windows one-click: double-click `run_dashboard.bat`.

## 🔌 API

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard UI |
| `GET /api/health` | Service + model status |
| `GET /api/decision?hour=&day=&weather=&A=&B=&C=&duration=` | Per-junction signal plan, predictions, forecast, sensors, environmental estimate |

## 📁 Project structure

```
├── dashboard.html          # Command-center UI (single page, no build step)
├── server.py               # FastAPI backend — decision engine
├── train_model.py          # Trains the classifier + forecaster
├── models/                 # Trained models (joblib) + metrics
├── data/                   # Synthetic benchmark dataset
├── docs/screenshots/       # README images
├── requirements.txt
├── Procfile / render.yaml  # Deployment configs
└── run_dashboard.bat       # Windows launcher
```

## ⚠️ Notes & limitations

Training data is synthetic and the traffic stream is simulated — the system is
not connected to real signals, cameras or IoT devices. Signal recommendations
are decision support, not a certified traffic-control algorithm; real
deployment would require calibrated field data and traffic-engineering
validation. Environmental figures are simulation-derived estimates, not
measurements.
