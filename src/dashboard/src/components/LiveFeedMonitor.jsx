import { useState } from "react";

const TIER_COLOR = { LOW: "#4a90d9", MEDIUM: "#d9a44a", HIGH: "#e0682d", CRITICAL: "#e02d2d" };

export default function LiveFeedMonitor({ liveAlerts, pipelineStats }) {
  const [selectedZone, setSelectedZone] = useState(null);

  const zones = ["Zone-Walkway", "Zone-Equipment", "Zone-Panel", "Zone-Forklift"];
  const zoneStatus = (zone) => {
    const recent = liveAlerts.find((a) => a.zone === zone);
    if (!recent) return { tier: null, label: "No violation detected" };
    return { tier: recent.severity, label: recent.behavior_label };
  };

  return (
    <div className="panel">
      <h3 style={{ marginTop: 0 }}>Live Feed Monitor</h3>
      <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
        Simulated camera zone status. Click "Run Pipeline" above to process clips —
        HIGH/CRITICAL events render here in real time as they're detected.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
        {zones.map((zone) => {
          const status = zoneStatus(zone);
          return (
            <div
              key={zone}
              onClick={() => setSelectedZone(zone)}
              style={{
                border: `1px solid ${status.tier ? TIER_COLOR[status.tier] : "#262b38"}`,
                borderRadius: 8,
                padding: 14,
                cursor: "pointer",
                background: status.tier ? `${TIER_COLOR[status.tier]}15` : "transparent",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ fontSize: 13 }}>{zone}</strong>
                {status.tier && (
                  <span className={`severity-badge severity-${status.tier}`}>{status.tier}</span>
                )}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 6 }}>
                {status.label}
              </div>
            </div>
          );
        })}
      </div>

      {pipelineStats && (
        <div style={{ marginTop: 20, fontSize: 12, color: "var(--text-dim)" }}>
          Last run: {pipelineStats.clips_processed} clip(s) processed ·{" "}
          {JSON.stringify(pipelineStats.severities_by_tier)}
        </div>
      )}
    </div>
  );
}
