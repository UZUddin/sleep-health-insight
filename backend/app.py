# backend/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
import uvicorn

from zipfile import ZipFile
from io import BytesIO

# ---------------------------------------------------------
# FastAPI app + CORS
# ---------------------------------------------------------

app = FastAPI(title="Sleep Health Insight API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Frontend build (if present)
# ---------------------------------------------------------

FRONTEND_DIR = Path(__file__).parent / "build"

# Serve static assets if build exists
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
        raise HTTPException(
            status_code=404,
            detail="Frontend build not found. Run `npm run build` and copy to backend/build.",
        )
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found in frontend build.")
    return FileResponse(index_file)


# ---------------------------------------------------------
# Sleep data handling (global in-memory cache)
# ---------------------------------------------------------

# Per-night metrics, one entry per date:
# {
#   "date": "YYYY-MM-DD",
#   "total_sleep_hours": float,
#   "rem_sleep_hours": float,
#   "nonrem_sleep_hours": float,
#   "rem_percentage": float | None,
#   "avg_hr": float | None,
#   "avg_hrv": float | None,
#   "avg_resp": float | None,
# }
nights: List[Dict] = []
summary_cache: Optional[Dict] = None
MAX_NIGHTS = 30


def get_recent_nights() -> List[Dict]:
    """
    Return up to the most recent MAX_NIGHTS entries from 'nights',
    sorted by date ascending.
    """
    if not nights:
        return []
    sorted_n = sorted(nights, key=lambda n: n["date"])
    return sorted_n[-MAX_NIGHTS:]


def compute_sleep_summary(nights_list: List[Dict]) -> Dict:
    """
    Take the nights list and compute the summary that the frontend expects.
    """
    if not nights_list:
        return {}

    n = len(nights_list)

    avg_total_sleep = sum(night["total_sleep_hours"] for night in nights_list) / n

    def safe_avg(key: str):
        vals = [night[key] for night in nights_list if night.get(key) is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    avg_hr = safe_avg("avg_hr")
    avg_hrv = safe_avg("avg_hrv")
    avg_resp = safe_avg("avg_resp")
    avg_rem_pct = safe_avg("rem_percentage")

    return {
        "nights": n,
        "avg_total_sleep": round(avg_total_sleep, 2),
        "avg_hr": round(avg_hr, 1) if avg_hr is not None else None,
        "avg_hrv": round(avg_hrv, 1) if avg_hrv is not None else None,
        "avg_resp_rate": round(avg_resp, 1) if avg_resp is not None else None,
        "avg_rem_pct": round(avg_rem_pct, 1) if avg_rem_pct is not None else None,
    }


def parse_apple_health_sleep_xml_stream(file_obj) -> None:
    """
    Stream-parse Apple Health XML to avoid loading it all into memory.

    Builds global `nights` with per-night metrics:
      - total_sleep_hours
      - rem_sleep_hours / nonrem_sleep_hours
      - rem_percentage
      - average heart rate
      - average HRV
      - average respiratory rate
    """
    global nights
    nights = []

    # Raw collections
    sleep_segments = []  # list of (start_dt, end_dt, stage)
    hr_points: List[tuple[datetime, float]] = []
    hrv_points: List[tuple[datetime, float]] = []
    resp_points: List[tuple[datetime, float]] = []

    # Example Apple Health timestamp: "2024-11-01 01:23:45 -0500"
    dt_fmt = "%Y-%m-%d %H:%M:%S %z"

    # Ensure we read from the beginning
    try:
        file_obj.seek(0)
    except Exception:
        pass

    context = ET.iterparse(file_obj, events=("start", "end"))
    _, root = next(context)  # Grab root

    def map_stage(value_str: Optional[str]) -> str:
        """
        Map Apple Health sleep category values into coarse stages:
          - ASLEEP_REM
          - ASLEEP_DEEP
          - ASLEEP_CORE
          - ASLEEP
        """
        if not value_str:
            return "ASLEEP"
        v = value_str.upper()
        if "REM" in v:
            return "ASLEEP_REM"
        if "DEEP" in v:
            return "ASLEEP_DEEP"
        if "CORE" in v:
            return "ASLEEP_CORE"
        if "ASLEEP" in v:
            return "ASLEEP"
        return "ASLEEP"

    for event, elem in context:
        if event == "end" and elem.tag == "Record":
            r_type = elem.get("type") or ""
            start_str = elem.get("startDate")
            end_str = elem.get("endDate")
            value_str = elem.get("value")

            if not start_str:
                elem.clear()
                continue

            try:
                start_dt = datetime.strptime(start_str, dt_fmt)
            except Exception:
                elem.clear()
                continue

            # ---- Sleep segments (ASLEEP, REM vs non-REM) ----
            if "SleepAnalysis" in r_type and end_str:
                try:
                    end_dt = datetime.strptime(end_str, dt_fmt)
                    stage = map_stage(value_str)
                    sleep_segments.append((start_dt, end_dt, stage))
                except Exception:
                    pass

            # ---- Heart Rate ----
            elif "HeartRate" in r_type and "Variability" not in r_type and value_str:
                try:
                    hr_points.append((start_dt, float(value_str)))
                except Exception:
                    pass

            # ---- Heart Rate Variability (SDNN) ----
            elif "HeartRateVariability" in r_type and value_str:
                try:
                    hrv_points.append((start_dt, float(value_str)))
                except Exception:
                    pass

            # ---- Respiratory Rate ----
            elif "RespiratoryRate" in r_type and value_str:
                try:
                    resp_points.append((start_dt, float(value_str)))
                except Exception:
                    pass

            # free memory for processed elements
            elem.clear()
            root.clear()

    # Keep only true "asleep" segments (ignore in-bed/awake)
    asleep_segments = [s for s in sleep_segments if s[2] and "ASLEEP" in s[2]]

    # Group by night
    nights_map: Dict[str, Dict[str, List]] = {}

    def nb(date_str: str) -> Dict[str, List]:
        if date_str not in nights_map:
            nights_map[date_str] = {
                "segments": [],  # (start, end, stage)
                "hr": [],
                "hrv": [],
                "resp": [],
            }
        return nights_map[date_str]

    # Add sleep segments to each night
    for s_start, s_end, stage in asleep_segments:
        night_date = s_start.date().isoformat()
        nb(night_date)["segments"].append((s_start, s_end, stage))

    # Assign HR / HRV / Resp points into whichever asleep segment they fall
    def assign_points(points: List[tuple[datetime, float]], key: str) -> None:
        for ts, val in points:
            for s_start, s_end, _stage in asleep_segments:
                if s_start <= ts <= s_end:
                    night_date = s_start.date().isoformat()
                    nb(night_date)[key].append(val)
                    break

    assign_points(hr_points, "hr")
    assign_points(hrv_points, "hrv")
    assign_points(resp_points, "resp")

    # Collapse into final nights list
    nights = []
    for date_str, raw in nights_map.items():
        total_sleep_hours = 0.0
        rem_hours = 0.0
        non_rem_hours = 0.0

        for s_start, s_end, stage in raw["segments"]:
            dur = (s_end - s_start).total_seconds() / 3600.0
            total_sleep_hours += dur
            if stage and "REM" in stage:
                rem_hours += dur
            else:
                non_rem_hours += dur

        # Compute REM percentage
        rem_pct = (
            (rem_hours / total_sleep_hours) * 100.0
            if total_sleep_hours > 0
            else None
        )

        avg_hr = sum(raw["hr"]) / len(raw["hr"]) if raw["hr"] else None
        avg_hrv = sum(raw["hrv"]) / len(raw["hrv"]) if raw["hrv"] else None
        avg_resp = sum(raw["resp"]) / len(raw["resp"]) if raw["resp"] else None

        nights.append(
            {
                "date": date_str,
                "total_sleep_hours": total_sleep_hours,
                "rem_sleep_hours": rem_hours,
                "nonrem_sleep_hours": non_rem_hours,
                "rem_percentage": rem_pct,
                "avg_hr": avg_hr,
                "avg_hrv": avg_hrv,
                "avg_resp": avg_resp,
            }
        )


# ---------------------------------------------------------
# API endpoints
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Accepts either export.xml directly or the full Apple Health ZIP export.
    Parses sleep data into global `nights` and caches a summary.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    filename = (file.filename or "").lower()
    raw_bytes = await file.read()

    # 1) Extract XML bytes (from ZIP or raw XML)
    if filename.endswith(".zip"):
        try:
            with ZipFile(BytesIO(raw_bytes)) as z:
                candidates = [
                    name for name in z.namelist()
                    if name.lower().endswith("export.xml")
                ]
                if not candidates:
                    raise HTTPException(
                        status_code=400,
                        detail="No export.xml file found in the Apple Health ZIP."
                    )
                xml_bytes = z.read(candidates[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read ZIP file: {e}"
            )
    else:
        # assume the uploaded file is export.xml directly
        xml_bytes = raw_bytes

    # 2) Call streaming parser on a file-like object
    try:
        file_like = BytesIO(xml_bytes)
        parse_apple_health_sleep_xml_stream(file_like)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing Apple Health XML: {e}"
        )

    # 3) Compute and cache summary from global `nights`
    global summary_cache
    summary_cache = compute_sleep_summary(nights)

    return {
        "message": "Apple Health data uploaded and parsed successfully.",
        "nights": len(nights),
    }


@app.get("/summary")
def get_summary():
    """
    Return the cached summary from the most recent upload.
    """
    if not summary_cache:
        raise HTTPException(
            status_code=400,
            detail="No data available. Upload your Apple Health export first."
        )
    return summary_cache


@app.get("/nights")
def get_nights_timeseries():
    """
    Return per-night metrics for graphs:
    - date
    - total_sleep_hours
    - rem_sleep_hours
    - nonrem_sleep_hours
    - rem_percentage
    - avg_hr, avg_hrv, avg_resp
    """
    recent = get_recent_nights()
    if not recent:
        raise HTTPException(status_code=400, detail="No sleep data available. Upload a file first.")
    return {"nights": recent}


class ScoreRequest(BaseModel):
    features: Dict[str, float]


@app.post("/sleep-score")
def sleep_score(_body: ScoreRequest | None = None):
    """
    Compute a composite Sleep Score using:
      - total sleep duration
      - sleep regularity
      - average heart rate
      - heart rate variability (HRV)
      - respiratory rate
    Uses up to the most recent MAX_NIGHTS nights of data.
    """
    recent = get_recent_nights()
    if not recent:
        raise HTTPException(status_code=400, detail="No sleep data available. Upload a file first.")

    # ---- 1. Duration component (per night) ----
    duration_scores = []
    for n in recent:
        d = n["total_sleep_hours"]
        # Ideal 7–9 hours
        if 7 <= d <= 9:
            ds = 100
        else:
            penalty = min(abs(d - 8) * 10, 70)  # lose 10 points per hour away from 8, cap at 70
            ds = max(30, 100 - penalty)
        duration_scores.append(ds)

    avg_duration_score = sum(duration_scores) / len(duration_scores)

    # ---- 2. Sleep regularity (based on variation in total sleep) ----
    durations = [n["total_sleep_hours"] for n in recent]
    mean_dur = sum(durations) / len(durations)
    variance = sum((d - mean_dur) ** 2 for d in durations) / len(durations)
    std_dev = variance ** 0.5

    if std_dev < 0.5:
        regularity_score = 100
    elif std_dev < 1.5:
        regularity_score = 85
    else:
        regularity_score = 70

    # ---- 3. Heart rate component ----
    hr_values = [n["avg_hr"] for n in recent if n["avg_hr"] is not None]
    if hr_values:
        avg_hr = sum(hr_values) / len(hr_values)
        if 50 <= avg_hr <= 70:
            hr_score = 100
        else:
            hr_penalty = min(abs(avg_hr - 60) * 2, 40)
            hr_score = max(60, 100 - hr_penalty)
    else:
        hr_score = 75

    # ---- 4. HRV component ----
    hrv_values = [n["avg_hrv"] for n in recent if n["avg_hrv"] is not None]
    if hrv_values:
        avg_hrv = sum(hrv_values) / len(hrv_values)
        if avg_hrv >= 60:
            hrv_score = 100
        elif avg_hrv >= 40:
            hrv_score = 85
        else:
            hrv_score = 70
    else:
        hrv_score = 75

    # ---- 5. Respiratory rate component ----
    resp_values = [n["avg_resp"] for n in recent if n["avg_resp"] is not None]
    if resp_values:
        avg_resp = sum(resp_values) / len(resp_values)
        if 12 <= avg_resp <= 18:
            resp_score = 100
        else:
            resp_penalty = min(abs(avg_resp - 15) * 3, 40)
            resp_score = max(60, 100 - resp_penalty)
    else:
        resp_score = 75

    # ---- Combine components into final score ----
    final_score = (
        0.40 * avg_duration_score
        + 0.20 * regularity_score
        + 0.15 * hr_score
        + 0.15 * hrv_score
        + 0.10 * resp_score
    )

    final_score = round(final_score, 1)

    explanation_parts = [
        f"Duration component: {avg_duration_score:.1f}",
        f"Regularity component: {regularity_score:.1f}",
        f"Heart rate component: {hr_score:.1f}",
        f"HRV component: {hrv_score:.1f}",
        f"Respiratory rate component: {resp_score:.1f}",
    ]
    explanation = " | ".join(explanation_parts)

    return {
        "sleep_score": final_score,
        "message": "Composite Sleep Score based on the most recent nights of data (up to 30 days).",
        "n_nights": len(recent),
        "details": {
            "duration_score": round(avg_duration_score, 1),
            "regularity_score": round(regularity_score, 1),
            "hr_score": round(hr_score, 1),
            "hrv_score": round(hrv_score, 1),
            "resp_score": round(resp_score, 1),
        },
        "explanation": explanation,
    }


# ---------------------------------------------------------
# Local dev entrypoint
# ---------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
