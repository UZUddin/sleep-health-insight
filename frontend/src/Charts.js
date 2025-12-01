import React from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function buildDataset(labels, values, label, color) {
  return {
    labels,
    datasets: [
      {
        label,
        data: values,
        borderColor: color,
        backgroundColor: color,
        tension: 0.3,
        pointRadius: 2,
        fill: false,
      },
    ],
  };
}

export default function Charts({ nights }) {
  if (!nights || nights.length === 0) return null;
  const labels = nights.map((n) => n.date);
  const sleep = nights.map((n) => n.total_sleep_hours ?? null);
  const hr = nights.map((n) => (n.avg_hr ?? null));
  const hrv = nights.map((n) => (n.avg_hrv ?? null));
  const resp = nights.map((n) => (n.avg_resp ?? null));
  const rem = nights.map((n) => (n.rem_hours ?? null));
  const nonrem = nights.map((n) => (n.non_rem_hours ?? null));

  const opts = {
    responsive: true,
    plugins: {
      legend: { position: "top" },
      title: { display: false },
      tooltip: { intersect: false },
    },
    interaction: { mode: "index" },
    scales: { x: { ticks: { maxRotation: 0 } } },
  };
  const optsStack = {
    ...opts,
    scales: {
      ...opts.scales,
      y: { stacked: true },
    },
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16, marginTop: 16 }}>
      <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <h3 style={{ margin: 0, marginBottom: 8 }}>Total Sleep Hours</h3>
        <Line data={buildDataset(labels, sleep, "Sleep Hours", "#4f46e5")} options={opts} />
      </div>
      <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <h3 style={{ margin: 0, marginBottom: 8 }}>Average Heart Rate</h3>
        <Line data={buildDataset(labels, hr, "Avg HR", "#ef4444")} options={opts} />
      </div>
      <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <h3 style={{ margin: 0, marginBottom: 8 }}>Average HRV</h3>
        <Line data={buildDataset(labels, hrv, "Avg HRV", "#10b981")} options={opts} />
      </div>
      <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <h3 style={{ margin: 0, marginBottom: 8 }}>Average Respiratory Rate</h3>
        <Line data={buildDataset(labels, resp, "Avg Respiratory", "#f59e0b")} options={opts} />
      </div>
      <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <h3 style={{ margin: 0, marginBottom: 8 }}>REM vs Non-REM Sleep Hours</h3>
        <Line
          data={{
            labels,
            datasets: [
              { label: "REM", data: rem, borderColor: "#8b5cf6", backgroundColor: "#8b5cf6", tension: 0.3, pointRadius: 2, fill: true, stack: "sleep" },
              { label: "Non-REM", data: nonrem, borderColor: "#22c55e", backgroundColor: "#22c55e", tension: 0.3, pointRadius: 2, fill: true, stack: "sleep" },
            ],
          }}
          options={optsStack}
        />
      </div>
    </div>
  );
}
