import { useEffect, useState } from "react";
import LiveFeedMonitor from "./components/LiveFeedMonitor.jsx";
import AlertTimeline from "./components/AlertTimeline.jsx";
import HistoricalLog from "./components/HistoricalLog.jsx";
import { subscribeAlerts, runPipeline } from "./api.js";

export default function App() {
  const [tab, setTab] = useState("live");
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [bannerAlert, setBannerAlert] = useState(null);
  const [running, setRunning] = useState(false);
  const [pipelineStats, setPipelineStats] = useState(null);

  useEffect(() => {
    const unsubscribe = subscribeAlerts((alert) => {
      setLiveAlerts((prev) => [alert, ...prev].slice(0, 100));
      setBannerAlert(alert);
      setTimeout(() => setBannerAlert((cur) => (cur?.event_id === alert.event_id ? null : cur)), 4000);
    });
    return unsubscribe;
  }, []);

  const handleRunPipeline = async () => {
    setRunning(true);
    try {
      const result = await runPipeline();
      setPipelineStats(result.stats);
    } catch (e) {
      console.error(e);
      alert("Pipeline run failed — check the backend is running on :8000.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="app">
      {bannerAlert && (
        <div className={`alert-banner ${bannerAlert.severity === "HIGH" ? "high" : ""}`}>
          <strong>{bannerAlert.severity} ALERT</strong>
          <div>{bannerAlert.behavior_label} — {bannerAlert.zone}</div>
        </div>
      )}

      <div className="app-header">
        <h1>Factory Compliance & Alert Escalation System</h1>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div className="tabs">
            <button className={`tab-btn ${tab === "live" ? "active" : ""}`} onClick={() => setTab("live")}>
              Live Feed
            </button>
            <button className={`tab-btn ${tab === "timeline" ? "active" : ""}`} onClick={() => setTab("timeline")}>
              Alert Timeline
            </button>
            <button className={`tab-btn ${tab === "log" ? "active" : ""}`} onClick={() => setTab("log")}>
              Historical Log
            </button>
          </div>
          <button className="run-btn" onClick={handleRunPipeline} disabled={running}>
            {running ? "Running..." : "Run Pipeline"}
          </button>
        </div>
      </div>

      <div className="main">
        {tab === "live" && <LiveFeedMonitor liveAlerts={liveAlerts} pipelineStats={pipelineStats} />}
        {tab === "timeline" && <AlertTimeline liveAlerts={liveAlerts} />}
        {tab === "log" && <HistoricalLog />}
      </div>
    </div>
  );
}
