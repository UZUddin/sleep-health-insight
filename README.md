# **Sleep Health Insight**

*A web-based dashboard for analyzing Apple Health sleep data.*

Sleep Health Insight lets users upload their **Apple Health export (ZIP/XML)** and instantly view analytics, trends, visualizations, and a computed **Sleep Health Score**. All processing is local and privacy-preserving.

---

## **Features**

* Upload Apple Health XML/ZIP
* Automatic metric detection
* Sleep duration + REM/non-REM (if available)
* Heart rate, HRV, respiratory rate trends
* Environmental noise + snoring (if available)
* Interactive dashboard visualizations
* Sleep Health Score (0–100)
* Optional FHIR R4 Observation mapping
* No cloud storage — everything runs locally

---

## **Tech Stack**

**Frontend:** React (Chart.js)
**Backend:** FastAPI (Python)
**Data:** Apple Health XML → nightly metrics

## **Installation**

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

### Frontend (React)

```bash
cd frontend
npm install
npm start
```

* Backend → [http://127.0.0.1:8001](http://127.0.0.1:8001)
* Frontend → [http://localhost:3000](http://localhost:3000)

---

## **Exporting Apple Health Data**

On iPhone:
**Health app → Profile → Export All Health Data → Export**

Upload the ZIP directly to the dashboard UI.

---

## **API Endpoints**

| Method | Endpoint              | Description                 |
| ------ | --------------------- | --------------------------- |
| POST   | `/upload-health-data` | Upload Apple Health XML/ZIP |
| GET    | `/sleep-summary`      | Summary across all nights   |
| POST   | `/sleep-score`        | Compute Sleep Score         |

---

## **Sleep Score Components**

Weighted formula based on:

* Sleep duration
* Consistency
* REM ratio
* Heart rate stability
* Respiratory rate stability

Outputs a 0–100 score.

---

## **Future Enhancements**

* ML-based sleep quality predictions
* Better REM/NREM inference
* Mobile app with HealthKit
* FHIR server integration

---

