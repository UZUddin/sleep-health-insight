import React, { useState } from "react";
import "./App.css";

function parseScoreComponents(text) {
  if (!text || typeof text !== "string") return {};

  const getValue = (label) => {
    const regex = new RegExp(label + "\\s*:?\\s*([0-9]+(?:\\.[0-9]+)?)");
    const match = text.match(regex);
    return match ? parseFloat(match[1]) : null;
  };

  return {
    duration_component: getValue("Duration component"),
    regularity_component: getValue("Regularity component"),
    hr_component: getValue("Heart rate component"),
    hrv_component: getValue("HRV component"),
    rr_component: getValue("Respiratory rate component"),
  };
}

function Card({ title, step, children }) {
  return (
    <section className="card">
      <div className="card-header">
        {step && <span className="card-step">Step {step}</span>}
        <h2>{title}</h2>
      </div>
      <div className="card-body">{children}</div>
    </section>
  );
}

function Badge({ tone = "neutral", children }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

/**
 * Tiny bar-chart style sparkline for micro stats.
 */
function Sparkline({ data, getValue, label, unit = "" }) {
  if (!data || data.length === 0) return null;

  const values = data
    .map((d) => getValue(d))
    .filter(
      (v) => v !== null && v !== undefined && !Number.isNaN(Number(v))
    );

  if (!values.length) {
    return (
      <div className="sparkline-card">
        <div className="sparkline-header">
          <span className="sparkline-label">{label}</span>
          <span className="sparkline-meta">No data</span>
        </div>
      </div>
    );
  }

  const max = Math.max(...values);
  const lastVal = values[values.length - 1];
  const avgVal = values.reduce((a, b) => a + b, 0) / values.length;

  const format = (v) =>
    typeof v === "number" ? v.toFixed(1) : String(v);

  return (
    <div className="sparkline-card">
      <div className="sparkline-header">
        <span className="sparkline-label">{label}</span>
        <span className="sparkline-meta">
          {format(lastVal)}
          {unit} • avg {format(avgVal)}
          {unit}
        </span>
      </div>
      <div className="sparkline-bars">
        {data.map((d, idx) => {
          const raw = getValue(d);
          const v =
            raw === null ||
            raw === undefined ||
            Number.isNaN(Number(raw))
              ? null
              : Number(raw);

          if (v === null || max === 0) {
            return (
              <div
                key={idx}
                className="spark-bar spark-bar-empty"
                title="No data"
              />
            );
          }
          const height = (v / max) * 100;
          return (
            <div
              key={idx}
              className="spark-bar"
              style={{ height: `${height}%` }}
              title={`${format(v)}${unit}`}
            />
          );
        })}
      </div>
    </div>
  );
}

function App() {
  const [uploadMessage, setUploadMessage] = useState("");
  const [summary, setSummary] = useState(null);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(false);

  // nightly timeseries for micro graphs
  const [nights, setNights] = useState([]);
  const [nightsError, setNightsError] = useState(null);

  // collapsible sections
  const [showBreakdown, setShowBreakdown] = useState(true);
  const [showTrends, setShowTrends] = useState(true);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setUploadMessage("");
    setSummary(null);
    setScore(null);
    setNights([]);
    setNightsError(null);

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

  // Fetch both summary + nightly timeseries (for graphs)
  const fetchSummary = async () => {
    setLoading(true);
    setSummary(null);
    setNights([]);
    setNightsError(null);

    try {
      const [summaryRes, nightsRes] = await Promise.all([
        fetch("/summary"),
        fetch("/nights"),
      ]);

      const summaryData = await summaryRes.json();
      const nightsData = await nightsRes.json();

      if (!summaryRes.ok) {
        throw new Error(summaryData.detail || "Error getting summary");
      }
      if (!nightsRes.ok) {
        throw new Error(nightsData.detail || "Error getting nightly data");
      }

      setSummary(summaryData);
      setNights(nightsData.nights || []);
    } catch (err) {
      setSummary({ error: err.message });
      setNightsError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchScore = async () => {
    setLoading(true);
    setScore(null);
    setNightsError(null);

    try {
      // Fetch SCORE
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

      const components = parseScoreComponents(
        data.explanation || data.message || ""
      );

      setScore({
        ...data,
        ...components,
      });

      // Fetch nights ONLY if we don’t already have them
      if (!nights || nights.length === 0) {
        const nightsRes = await fetch("/nights");
        const nightsData = await nightsRes.json();

        if (!nightsRes.ok) {
          throw new Error(nightsData.detail || "Error getting nightly data");
        }

        setNights(nightsData.nights || []);
      }
    } catch (err) {
      setScore({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const isErrorUpload = uploadMessage.startsWith("Error:");
  const hasSummaryError = summary && summary.error;
  const hasScoreError = score && score.error;

  const sleepScoreValue =
    score && (score.score ?? score.sleep_score ?? null);

  let scoreTone = "neutral";
  if (typeof sleepScoreValue === "number") {
    if (sleepScoreValue >= 80) scoreTone = "good";
    else if (sleepScoreValue >= 60) scoreTone = "warn";
    else scoreTone = "bad";
  }

  return (
    <div className="app-root">

      <header className="app-header">
        <div className="hero-row">
          <div className="hero-left">
            <div className="hero-logo">
              <div className="hero-orb"></div>
              <div>
                <div className="hero-title">Sleep Health Insight</div>
                <div className="hero-sub">Understand your sleep at a glance</div>
              </div>
            </div>

            <p className="hero-tagline">
              Upload your Apple Health export and get a clean, visual snapshot of your night-to-night sleep patterns.
            </p>
          </div>

          <div className="hero-badge">
            <span className="hero-dot" />
            <span>Beta</span>
          </div>
        </div>
      </header>

      {loading && (
        <div className="loading-banner">
          <span className="spinner" />
          <span>Analyzing your data…</span>
        </div>
      )}

      <main className="app-main">
        {/* Upload card */}
        <Card title="Upload Apple Health export" step={1}>
          <p className="card-text">
            Export your Apple Health data from your iPhone and upload the{" "}
            <strong>export.xml</strong> file here.
          </p>
          <label className="file-input-label">
            <input
              type="file"
              accept=".xml"
              onChange={handleFileUpload}
              className="file-input"
            />
            <span>Choose XML file</span>
          </label>

          {uploadMessage && (
            <p
              className={`status-text ${
                isErrorUpload ? "status-error" : "status-success"
              }`}
            >
              {uploadMessage}
            </p>
          )}
        </Card>

        {/* Analytics card */}
        <Card title="View your sleep analytics" step={2}>
          <p className="card-text">
            Once your file is processed, you can view a simple sleep summary and
            a computed <strong>Sleep Health Score</strong>.
          </p>

          <div className="button-row">
            <button className="btn" onClick={fetchSummary} disabled={loading}>
              View Sleep Summary
            </button>
            <button
              className="btn btn-secondary"
              onClick={fetchScore}
              disabled={loading}
            >
              Get Sleep Score
            </button>
          </div>

          {/* Summary block */}
          {summary && !hasSummaryError && (
            <div className="summary-panel">
              <div className="summary-header">
                <h3>Sleep Summary</h3>
                <Badge>Overview</Badge>
              </div>
              <div className="summary-grid">
                <div className="summary-item">
                  <span className="summary-label">Nights tracked</span>
                  <span className="summary-value">
                    {summary.nights ?? summary.n_nights ?? "—"}
                  </span>
                </div>

                <div className="summary-item">
                  <span className="summary-label">Avg total sleep</span>
                  <span className="summary-value">
                    {summary.avg_total_sleep ??
                      summary.avg_sleep_hours ??
                      "—"}{" "}
                    <span className="summary-unit">hrs / night</span>
                  </span>
                </div>

                {summary.avg_hr !== undefined && summary.avg_hr !== null && (
                  <div className="summary-item">
                    <span className="summary-label">
                      Avg night heart rate
                    </span>
                    <span className="summary-value">
                      {summary.avg_hr}
                      <span className="summary-unit"> bpm</span>
                    </span>
                  </div>
                )}

                {summary.avg_hrv !== undefined &&
                  summary.avg_hrv !== null && (
                    <div className="summary-item">
                      <span className="summary-label">Avg HRV</span>
                      <span className="summary-value">
                        {summary.avg_hrv}
                        <span className="summary-unit"> ms</span>
                      </span>
                    </div>
                  )}

                {summary.avg_resp_rate !== undefined &&
                  summary.avg_resp_rate !== null && (
                    <div className="summary-item">
                      <span className="summary-label">
                        Avg respiratory rate
                      </span>
                      <span className="summary-value">
                        {summary.avg_resp_rate}
                        <span className="summary-unit"> br/min</span>
                      </span>
                    </div>
                  )}

                {summary.avg_rem_pct !== undefined &&
                  summary.avg_rem_pct !== null && (
                    <div className="summary-item">
                      <span className="summary-label">
                        Avg REM sleep percentage
                      </span>
                      <span className="summary-value">
                        {summary.avg_rem_pct}
                        <span className="summary-unit"> %</span>
                      </span>
                    </div>
                  )}
              </div>
            </div>
          )}

          {hasSummaryError && (
            <p className="status-text status-error">
              Error loading summary: {summary.error}
            </p>
          )}

          {/* SCORE SECTION */}
          {score && !hasScoreError && (
            <>
              <div className="score-panel">
                <div className="score-header">
                  <h3>Sleep Health Score</h3>
                  <Badge tone={scoreTone}>
                    {scoreTone === "good"
                      ? "Good"
                      : scoreTone === "warn"
                      ? "Fair"
                      : scoreTone === "bad"
                      ? "Needs attention"
                      : "Score"}
                  </Badge>
                </div>

                <div className="score-body">
                  <div className={`score-circle score-${scoreTone}`}>
                    <span>
                      {sleepScoreValue !== null ? sleepScoreValue : "—"}
                    </span>
                    <span className="score-max">/ 100</span>
                  </div>
                  <p className="score-text">
                    This score combines your sleep duration, regularity, heart
                    rate, HRV, and respiratory rate into one overall sleep
                    health number. Use the sections below to dig into the
                    details and trends.
                  </p>
                </div>
              </div>

              {/* SCORE BREAKDOWN SECTION (own bubble, collapsible) */}
              <div className="section-panel">
                <div
                  className="section-header"
                  onClick={() => setShowBreakdown((v) => !v)}
                >
                  <div className="section-title">
                    <h3>Score breakdown</h3>
                    <Badge>Details</Badge>
                  </div>
                  <button
                    type="button"
                    className="collapse-toggle"
                    aria-label="Toggle score breakdown"
                  >
                    {showBreakdown ? "▾" : "▸"}
                  </button>
                </div>

                {showBreakdown && (
                  <div className="score-breakdown">
                    <div className="breakdown-grid">
                      <div className="breakdown-item">
                        <span className="breakdown-icon">🕒</span>
                        <div className="breakdown-info">
                          <strong>
                            Duration: {score.duration_component ?? "—"}
                          </strong>
                          <p>Total sleep time per night.</p>
                          <small className="range">
                            Healthy: 7–9 hours per night
                          </small>
                        </div>
                      </div>

                      <div className="breakdown-item">
                        <span className="breakdown-icon">📅</span>
                        <div className="breakdown-info">
                          <strong>
                            Regularity: {score.regularity_component ?? "—"}
                          </strong>
                          <p>Consistency of bed and wake times.</p>
                          <small className="range">
                            Healthy: ≤ 30–45 min variation
                          </small>
                        </div>
                      </div>

                      <div className="breakdown-item">
                        <span className="breakdown-icon">❤️</span>
                        <div className="breakdown-info">
                          <strong>
                            Heart rate: {score.hr_component ?? "—"}
                          </strong>
                          <p>Average heart rate during sleep.</p>
                          <small className="range">
                            Healthy: ~50–65 bpm (adult)
                          </small>
                        </div>
                      </div>

                      <div className="breakdown-item">
                        <span className="breakdown-icon">📉</span>
                        <div className="breakdown-info">
                          <strong>HRV: {score.hrv_component ?? "—"}</strong>
                          <p>Nighttime heart rate variability.</p>
                          <small className="range">
                            Healthy: ~60–90 ms (age dependent)
                          </small>
                        </div>
                      </div>

                      <div className="breakdown-item">
                        <span className="breakdown-icon">🌬</span>
                        <div className="breakdown-info">
                          <strong>
                            Respiratory rate: {score.rr_component ?? "—"}
                          </strong>
                          <p>Average breaths per minute during sleep.</p>
                          <small className="range">
                            Healthy: 12–20 breaths/min
                          </small>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* TRENDS SECTION (own bubble, collapsible) */}
              <div className="section-panel">
                <div
                  className="section-header"
                  onClick={() => setShowTrends((v) => !v)}
                >
                  <div className="section-title">
                    <h3>Trends across recent nights</h3>
                    <Badge>Micro stats</Badge>
                  </div>
                  <button
                    type="button"
                    className="collapse-toggle"
                    aria-label="Toggle trends section"
                  >
                    {showTrends ? "▾" : "▸"}
                  </button>
                </div>

                {showTrends && (
                  <>
                    {nightsError && (
                      <p
                        className="status-text status-error"
                        style={{ marginTop: 4 }}
                      >
                        Error loading nightly trends: {nightsError}
                      </p>
                    )}

                    {nights.length > 0 && !nightsError && (
                      <div className="microstats-panel">
                        <div className="microstats-grid">
                          <Sparkline
                            label="Sleep duration (hrs)"
                            unit="h"
                            data={nights}
                            getValue={(n) => n.total_sleep_hours}
                          />
                          <Sparkline
                            label="Night HR (bpm)"
                            unit=" bpm"
                            data={nights}
                            getValue={(n) => n.avg_hr}
                          />
                          <Sparkline
                            label="HRV (ms)"
                            unit=" ms"
                            data={nights}
                            getValue={(n) => n.avg_hrv}
                          />
                          <Sparkline
                            label="Resp rate (br/min)"
                            unit=" br/min"
                            data={nights}
                            getValue={(n) => n.avg_resp}
                          />
                          <Sparkline
                            label="REM %"
                            unit="%"
                            data={nights}
                            getValue={(n) => n.rem_percentage}
                          />
                        </div>
                      </div>
                    )}

                    {nights.length === 0 && !nightsError && (
                      <p className="status-text" style={{ marginTop: 4 }}>
                        No nightly data available yet. Upload your Apple Health
                        export and view the summary or score to populate trends.
                      </p>
                    )}
                  </>
                )}
              </div>
            </>
          )}

          {hasScoreError && (
            <p className="status-text status-error">
              Error loading score: {score.error}
            </p>
          )}
        </Card>
      </main>
    </div>
  );
}

export default App;
