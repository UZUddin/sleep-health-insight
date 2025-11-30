import React, { useState } from "react";
import Charts from "./Charts";

function App() {
  const [uploadMessage, setUploadMessage] = useState("");
  const [summary, setSummary] = useState(null);
  const [score, setScore] = useState(null);
  const [nights, setNights] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setUploadMessage("");
    setSummary(null);
    setScore(null);
    setNights(null);

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      setUploadMessage(data.message || "File uploaded.");
    } catch (err) {
      setUploadMessage("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    setLoading(true);
    setSummary(null);
    try {
      const res = await fetch("/summary");
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Error getting summary");
      }
      setSummary(data);
    } catch (err) {
      setSummary({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const fetchScore = async () => {
    setLoading(true);
    setScore(null);
    try {
      // Your backend currently has POST /sleep-score expecting a JSON body.
      // We'll send a simple dummy feature dictionary for now.
      const res = await fetch("/sleep-score", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          features: {
            avg_hr: 62.0,
            resp_rate: 14.5,
          },
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Error getting score");
      }
      setScore(data);
    } catch (err) {
      setScore({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const fetchNights = async () => {
    setLoading(true);
    setNights(null);
    try {
      const res = await fetch("/nights");
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Error getting nights");
      }
      setNights(data);
    } catch (err) {
      setNights({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: 900,
        margin: "0 auto",
        padding: "24px",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <h1>Sleep Health Insight</h1>
      <p>
        Upload your Apple Health export and view a simple{" "}
        <strong>sleep summary</strong> and <strong>Sleep Score</strong>.
      </p>

      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 12,
          padding: 16,
          marginTop: 16,
        }}
      >
        <h2>1. Upload Apple Health XML</h2>
        <input type="file" accept=".xml" onChange={handleFileUpload} />
        {loading && <p>Loading...</p>}
        {uploadMessage && (
          <p style={{ marginTop: 8 }}>
            <strong>{uploadMessage}</strong>
          </p>
        )}
      </section>

      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 12,
          padding: 16,
          marginTop: 16,
        }}
      >
        <h2>2. View Analytics</h2>
        <button onClick={fetchSummary} style={{ marginRight: 8 }}>
          View Sleep Summary
        </button>
        <button onClick={fetchScore} style={{ marginRight: 8 }}>Get Sleep Score</button>
        <button onClick={fetchNights}>View Trends</button>

        {summary && !summary.error && (
          <div style={{ marginTop: 16 }}>
            <h3>Sleep Summary</h3>
            <p>
              <strong>Nights tracked:</strong> {summary.nights ?? summary.n_nights}
            </p>
            <p>
              <strong>Average total sleep:</strong>{" "}
              {summary.avg_total_sleep ?? summary.avg_sleep_hours} hours
            </p>
            {summary.avg_hr !== undefined && (
              <p>
                <strong>Average heart rate:</strong> {summary.avg_hr} bpm
              </p>
            )}
          </div>
        )}
        {summary && summary.error && (
          <p style={{ marginTop: 16, color: "red" }}>Error: {summary.error}</p>
        )}

        {score && !score.error && (
          <div style={{ marginTop: 16 }}>
            <h3>Sleep Score</h3>
            <p style={{ fontSize: 32, margin: 0 }}>{score.score ?? score.sleep_score} / 100</p>
            <p>{score.explanation ?? score.message}</p>
          </div>
        )}
        {score && score.error && (
          <p style={{ marginTop: 16, color: "red" }}>Error: {score.error}</p>
        )}

        {nights && !nights.error && <Charts nights={nights} />}
        {nights && nights.error && (
          <p style={{ marginTop: 16, color: "red" }}>Error: {nights.error}</p>
        )}
      </section>
    </div>
  );
}

export default App;
