import { useEffect, useState } from "react";
import { fetchReports, exportUrl } from "../api.js";

export default function HistoricalLog() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    severity: "",
    behavior_class: "",
    start_date: "",
    end_date: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchReports(filters);
      setReports(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="panel">
      <h3 style={{ marginTop: 0 }}>Historical Log & Export</h3>

      <div className="filters">
        <select
          value={filters.severity}
          onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
        >
          <option value="">All severities</option>
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>

        <select
          value={filters.behavior_class}
          onChange={(e) => setFilters({ ...filters, behavior_class: e.target.value })}
        >
          <option value="">All behavior classes</option>
          <option value="pedestrian_movement">Pedestrian Movement</option>
          <option value="equipment_intervention">Equipment Intervention</option>
          <option value="electrical_panel_management">Electrical Panel</option>
          <option value="forklift_load_management">Forklift Load</option>
        </select>

        <input
          type="date"
          value={filters.start_date}
          onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
        />
        <input
          type="date"
          value={filters.end_date}
          onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
        />

        <button className="run-btn" onClick={load} disabled={loading}>
          {loading ? "Loading..." : "Apply Filters"}
        </button>
        <a className="export-btn" href={exportUrl("csv", filters)}>Export CSV</a>
        <a className="export-btn" href={exportUrl("json", filters)}>Export JSON</a>
      </div>

      {reports.length === 0 ? (
        <div className="empty-state">No reports match the current filters.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Clip</th><th>Zone</th><th>Behavior</th>
              <th>Policy Ref</th><th>Severity</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.event_id}>
                <td>{r.timestamp}</td>
                <td>{r.clip_id}</td>
                <td>{r.zone}</td>
                <td>{r.behavior_label}</td>
                <td>{r.policy_rule_ref}</td>
                <td><span className={`severity-badge severity-${r.severity}`}>{r.severity}</span></td>
                <td>{r.escalation_action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
