# backend/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List
from pathlib import Path
from io import BytesIO
import xml.etree.ElementTree as ET
from datetime import datetime
import uvicorn

# Path to React build folder
FRONTEND_DIR = Path(__file__).parent / "build"

app = FastAPI(title="Sleep Health Insight API", docs_url="/docs")

# --- CORS: allow React dev + deployed clients ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for class project
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Serve React static files (only if build exists) ---
if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIR / "static"),
        name="static",
    )

@app.get("/")
async def serve_frontend():
    """
    Serve the React app's index.html at the root.
    If the build folder is missing, return a clear 404 error.
    """
    if not FRONTEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build and copy to backend/build.")
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found in frontend build.")
    return FileResponse(index_file)


# --------- Sleep data handling ---------
sleep_records: List[dict] = []  # {start, end, duration_hours}

def parse_apple_health_sleep_xml(file_bytes: bytes):
    """
    Minimal Apple Health XML sleep parser.
    """
    global sleep_records
    sleep_records = []

    try:
        tree = ET.parse(BytesIO(file_bytes))
        root = tree.getroot()

        for record in root.findall("Record"):
            record_type = record.get("type", "")
            if "SleepAnalysis" in record_type:
                start_str = record.get("startDate")
                end_str = record.get("endDate")
                if not start_str or not end_str:
                    continue

                fmt = "%Y-%m-%d %H:%M:%S %z"
                try:
                    start_dt = datetime.strptime(start_str, fmt)
                    end_dt = datetime.strptime(end_str, fmt)
                except Exception:
                    # skip records with weird datetime formats
                    continue

                duration = (end_dt - start_dt).total_seconds() / 3600.0
                sleep_records.append(
                    {
                        "start": start_dt,
                        "end": end_dt,
                        "duration_hours": duration,
                    }
                )
    except Exception:
        sleep_records = []


# --------- API endpoints ---------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Upload Apple Health XML and parse sleep records.
    """
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=400, detail="Please upload an Apple Health XML (.xml) file.")
    content = await file.read()
    parse_apple_health_sleep_xml(content)
    if not sleep_records:
        return {"message": "File uploaded, but no sleep records were detected."}
    return {"message": f"File uploaded. Parsed {len(sleep_records)} sleep records."}


@app.get("/summary")
def summary():
    """
    Return basic summary statistics for sleep.
    """
    if not sleep_records:
        raise HTTPException(status_code=400, detail="No sleep data available. Upload a file first.")

    n_nights = len(sleep_records)
    total_hours = sum(r["duration_hours"] for r in sleep_records)
    avg_sleep = total_hours / n_nights

    starts = [r["start"] for r in sleep_records]
    ends = [r["end"] for r in sleep_records]
    first_night = min(starts).date().isoformat()
    last_night = max(ends).date().isoformat()

    return {
        "n_nights": n_nights,
        "avg_sleep_hours": round(avg_sleep, 2),
        "total_sleep_hours": round(total_hours, 2),
        "first_night": first_night,
        "last_night": last_night,
    }


class ScoreRequest(BaseModel):
    features: Dict[str, float]


@app.post("/sleep-score")
def sleep_score(req: ScoreRequest):
    """
    Dummy scoring based on provided features (you can expand this),
    OR you can ignore req.features and compute directly from sleep_records.
    """
    # Simple placeholder: start at 75 and nudge slightly by avg_hr if provided
    score = 75.0
    avg_hr = req.features.get("avg_hr")
    if avg_hr is not None:
        if 50 <= avg_hr <= 70:
            score += 5
        else:
            score -= 5

    score = max(0.0, min(100.0, score))

    return {
        "score": round(score, 1),
        "explanation": "Demo score based on placeholder rules. Can be extended with real analytics.",
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
