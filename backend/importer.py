# backend/importer.py
from lxml import etree
from datetime import datetime, timezone
from typing import Iterable, Tuple, Optional
import sqlite3

# Apple exports use keys like:
# <Record type="HKQuantityTypeIdentifierHeartRate"
#         unit="count/min"
#         value="71"
#         startDate="2025-01-02 03:14:00 -0500"
#         endDate="2025-01-02 03:14:00 -0500" ... />

def _parse_apple_date(s: str) -> int:
    # Example: "2025-01-02 03:14:00 -0500"
    # Convert to epoch milliseconds UTC
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)

# Sleep code mapping (Apple historically used category values 0..5; many exports only have INBED/ASLEEP)
SLEEP_VALUE_MAP = {
    "0": "INBED",
    "1": "ASLEEP",
    "2": "AWARENESS",
    "3": "ASLEEP_CORE",
    "4": "ASLEEP_DEEP",
    "5": "ASLEEP_REM",
}

def import_health_xml(xml_path: str, conn: sqlite3.Connection) -> Tuple[int, int]:
    """Stream-parse the XML and insert records in batches.
    Returns (hr_count, sleep_count)."""
    context = etree.iterparse(xml_path, events=("end",), tag=("Record",))
    hr_batch = []
    sleep_batch = []
    HR_BATCH_SIZE = 2000
    SLEEP_BATCH_SIZE = 1000

    hr_count = 0
    sleep_count = 0

    for event, elem in context:
        typ = elem.get("type") or ""
        if typ == "HKQuantityTypeIdentifierHeartRate":
            val = elem.get("value")
            start = elem.get("startDate")
            if val and start:
                try:
                    ts = _parse_apple_date(start)
                    hr_batch.append((ts, float(val)))
                    if len(hr_batch) >= HR_BATCH_SIZE:
                        conn.executemany("INSERT INTO heart_rate(ts, value) VALUES (?,?)", hr_batch)
                        hr_count += len(hr_batch)
                        hr_batch.clear()
                except Exception:
                    pass  # ignore malformed
        elif typ == "HKCategoryTypeIdentifierSleepAnalysis":
            start = elem.get("startDate")
            end = elem.get("endDate")
            value = elem.get("value")  # category integer as string
            if start and end:
                try:
                    s = _parse_apple_date(start)
                    e = _parse_apple_date(end)
                    stage = SLEEP_VALUE_MAP.get(value or "", "ASLEEP")
                    sleep_batch.append((s, e, stage))
                    if len(sleep_batch) >= SLEEP_BATCH_SIZE:
                        conn.executemany(
                            "INSERT INTO sleep_epoch(start_ts, end_ts, stage) VALUES (?,?,?)",
                            sleep_batch,
                        )
                        sleep_count += len(sleep_batch)
                        sleep_batch.clear()
                except Exception:
                    pass

        # help the parser free memory
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    # flush remaining
    if hr_batch:
        conn.executemany("INSERT INTO heart_rate(ts, value) VALUES (?,?)", hr_batch)
        hr_count += len(hr_batch)
    if sleep_batch:
        conn.executemany(
            "INSERT INTO sleep_epoch(start_ts, end_ts, stage) VALUES (?,?,?)",
            sleep_batch,
        )
        sleep_count += len(sleep_batch)

    return hr_count, sleep_count
