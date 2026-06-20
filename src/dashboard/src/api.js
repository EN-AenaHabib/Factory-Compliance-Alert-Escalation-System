const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchReports(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v) params.append(k, v);
  });
  const res = await fetch(`${API_BASE}/api/reports?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch reports: ${res.status}`);
  return res.json();
}

export function exportUrl(format, filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v) params.append(k, v);
  });
  return `${API_BASE}/api/reports/export/${format}?${params.toString()}`;
}

export async function runPipeline() {
  const res = await fetch(`${API_BASE}/api/pipeline/run`, { method: "POST" });
  if (!res.ok) throw new Error(`Pipeline run failed: ${res.status}`);
  return res.json();
}

export function subscribeAlerts(onAlert) {
  const source = new EventSource(`${API_BASE}/api/stream/alerts`);
  source.addEventListener("alert", (e) => {
    try {
      onAlert(JSON.parse(e.data));
    } catch (err) {
      console.error("Failed to parse alert event", err);
    }
  });
  return () => source.close();
}

export { API_BASE };
