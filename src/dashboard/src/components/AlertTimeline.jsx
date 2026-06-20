export default function AlertTimeline({ liveAlerts }) {
  return (
    <div className="panel">
      <h3 style={{ marginTop: 0 }}>Alert Timeline Stream</h3>
      <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
        Real-time chronological stream of HIGH/CRITICAL compliance events (via SSE).
      </p>
      {liveAlerts.length === 0 ? (
        <div className="empty-state">No alerts yet. Run the pipeline to generate events.</div>
      ) : (
        <div style={{ maxHeight: 420, overflowY: "auto", marginTop: 12 }}>
          {liveAlerts.map((a) => (
            <div className="timeline-item" key={a.event_id}>
              <span className="timeline-time">{a.timestamp.slice(11, 19)}</span>
              <span className={`severity-badge severity-${a.severity}`}>{a.severity}</span>
              <div>
                <div><strong>{a.behavior_label}</strong> — {a.zone}</div>
                <div style={{ color: "var(--text-dim)" }}>
                  {a.description} (clip: {a.clip_id}, ref: {a.policy_section_ref})
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
