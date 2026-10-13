import React, { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { TaskBoard } from "../components/TaskBoard";

const gatewayUrl = import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:8580";

const emptyDashboard = {
  home_id: "HOME-DEMO",
  user_id: "USR-OWNER-1",
  devices: { items: [] },
  scenarios: { items: [] },
  rules: { items: [] },
  kpi: {
    command_reaction_ms: 0,
    target_command_reaction_ms: 1000,
    availability_pct: 0,
    target_availability_pct: 99.9,
    voice_accuracy_pct: 0,
    target_voice_accuracy_pct: 95,
    energy_forecast_kwh: 0,
  },
  command_logs: { items: [] },
  anomalies: { items: [] },
  users: { items: [] },
  mqtt_tls: { enabled: true, protocol: "TLSv1.3" },
  integrations: { items: [] },
  brands: { items: [] },
  notifications: { items: [] },
  weather: { temperature_c: 0, condition: "n/a", humidity_pct: 0 },
};

async function loadDashboard(homeId, userId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${homeId}/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard: ${response.status}`);
  }
  return response.json();
}

async function runVoiceCommand(homeId, userId, text) {
  const response = await fetch(`${gatewayUrl}/workflow/process-command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      home_id: homeId,
      source: "voice",
      command_text: text,
      actor_role: "owner",
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Command failed: ${response.status} ${detail}`);
  }
  return response.json();
}

async function runScenario(homeId, userId, scenarioId) {
  const response = await fetch(`${gatewayUrl}/workflow/run-scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      home_id: homeId,
      scenario_id: scenarioId,
      actor_role: "owner",
    }),
  });
  if (!response.ok) {
    throw new Error(`Scenario failed: ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const [homeId, setHomeId] = useState("HOME-DEMO");
  const [userId, setUserId] = useState("USR-OWNER-1");
  const [commandText, setCommandText] = useState("turn off living room light");
  const [theme, setTheme] = useState("light");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [lastWorkflow, setLastWorkflow] = useState(null);

  const refresh = async () => {
    try {
      setStatus("loading");
      const payload = await loadDashboard(homeId, userId);
      setDashboard({ ...emptyDashboard, ...payload });
      setStatus("succeeded");
      setError(null);
    } catch (err) {
      setStatus("failed");
      setError(err.message);
    }
  };

  useEffect(() => {
    refresh();
  }, [homeId, userId]);

  const sendCommand = async () => {
    try {
      const workflow = await runVoiceCommand(homeId, userId, commandText);
      setLastWorkflow(workflow);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const activateScenario = async (scenarioId) => {
    try {
      await runScenario(homeId, userId, scenarioId);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const statusLabel = useMemo(() => {
    if (status === "loading") {
      return "loading";
    }
    if (status === "failed") {
      return "Service unavailable";
    }
    return "live";
  }, [status]);

  const devices = dashboard.devices?.items || [];
  const scenarios = dashboard.scenarios?.items || [];
  const anomalies = dashboard.anomalies?.items || [];
  const notifications = dashboard.notifications?.items || [];

  return (
    <div className={`app theme-${theme}`}>
      <div className="background-orb orb-a" />
      <div className="background-orb orb-b" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">SmartHome Hub</p>
          <h1>Your connected home</h1>
          <p className="sub">
            Manage devices, run automation scenarios, process voice commands, and detect abnormal activity from a single
            control center.
          </p>
          <div className="hero-badges">
            <span>Behavior learning</span>
            <span>Energy forecast</span>
            <span>Anomaly detection</span>
            <span>Alice and Alexa integration</span>
          </div>
        </div>

        <div className="hero-panel">
          <label>
            Home ID
            <input value={homeId} onChange={(event) => setHomeId(event.target.value)} placeholder="HOME-DEMO" />
          </label>
          <label>
            User ID
            <input value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="USR-OWNER-1" />
          </label>
          <label>
            Voice command
            <input value={commandText} onChange={(event) => setCommandText(event.target.value)} placeholder="turn off living room light" />
          </label>
          <div className="hero-actions">
            <button onClick={sendCommand}>Run voice command</button>
            <button className="ghost" onClick={refresh}>
              Refresh
            </button>
            <button className="ghost" onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}>
              Theme
            </button>
          </div>
          <p className="status-line" role="status" aria-live="polite">Status: {statusLabel}</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard
          title="Command Latency"
          value={`${Number(dashboard.kpi?.command_reaction_ms || 0).toFixed(0)} ms`}
          target={`Target < ${dashboard.kpi?.target_command_reaction_ms || 1000} ms`}
          ok={Number(dashboard.kpi?.command_reaction_ms || 9999) <= Number(dashboard.kpi?.target_command_reaction_ms || 1000)}
        />
        <KpiCard
          title="Availability"
          value={`${Number(dashboard.kpi?.availability_pct || 0).toFixed(2)}%`}
          target={`Target ${dashboard.kpi?.target_availability_pct || 99.9}%`}
          ok={Number(dashboard.kpi?.availability_pct || 0) >= Number(dashboard.kpi?.target_availability_pct || 99.9)}
        />
        <KpiCard
          title="Voice Accuracy"
          value={`${Number(dashboard.kpi?.voice_accuracy_pct || 0).toFixed(2)}%`}
          target={`Target > ${dashboard.kpi?.target_voice_accuracy_pct || 95}%`}
          ok={Number(dashboard.kpi?.voice_accuracy_pct || 0) >= Number(dashboard.kpi?.target_voice_accuracy_pct || 95)}
        />
        <KpiCard title="Energy Forecast" value={`${Number(dashboard.kpi?.energy_forecast_kwh || 0).toFixed(2)} kWh`} target="Next 24h" ok />
      </section>

      {error ? <div className="error-banner" role="alert">{error}</div> : null}

      <section className="content-grid">
        <article className="panel panel-featured">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Devices</p>
              <h2>Home topology and live states</h2>
            </div>
            <span className="pill">{devices.length} devices</span>
          </div>
          <div className="metrics-row">
            <div>
              <strong>{dashboard.users?.count || 0}</strong>
              <span>users</span>
            </div>
            <div>
              <strong>{dashboard.rules?.count || 0}</strong>
              <span>automation rules</span>
            </div>
            <div>
              <strong>{dashboard.scenarios?.count || 0}</strong>
              <span>scenarios</span>
            </div>
            <div>
              <strong>{dashboard.mqtt_tls?.enabled ? "TLS on" : "TLS off"}</strong>
              <span>{dashboard.mqtt_tls?.protocol || "n/a"}</span>
            </div>
          </div>
          <TaskBoard devices={devices} />
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Scenarios</p>
              <h2>Automation actions</h2>
            </div>
            <span className="pill accent">{scenarios.length} available</span>
          </div>
          <div className="stack-list">
            {scenarios.map((scenario) => (
              <div className="stack-item" key={scenario.scenario_id}>
                <div>
                  <p className="stack-title">{scenario.name}</p>
                  <p className="stack-sub">{scenario.description}</p>
                </div>
                <button onClick={() => activateScenario(scenario.scenario_id)}>Run</button>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Anomalies</p>
              <h2>Safety watch</h2>
            </div>
            <span className="pill">{anomalies.length}</span>
          </div>
          <div className="stack-list">
            {anomalies.length ? (
              anomalies.map((item) => (
                <div className="stack-item" key={item.anomaly_id}>
                  <div>
                    <p className="stack-title">{item.metric}</p>
                    <p className="stack-sub">{item.message}</p>
                  </div>
                  <span>{item.severity}</span>
                </div>
              ))
            ) : (
              <div className="empty-board">No anomalies detected.</div>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Integrations</p>
              <h2>Brands and services</h2>
            </div>
            <span className="pill">{dashboard.integrations?.count || 0} syncs</span>
          </div>
          <div className="chip-list">
            {(dashboard.brands?.items || []).map((brand) => (
              <span key={brand}>{brand}</span>
            ))}
          </div>
          <div className="stack-list">
            {(dashboard.integrations?.items || []).slice(-4).reverse().map((item) => (
              <div className="stack-item" key={item.sync_id}>
                <div>
                  <p className="stack-title">{item.system_name}</p>
                  <p className="stack-sub">{item.status}</p>
                </div>
                <span>{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel-analytics">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Activity</p>
              <h2>Recent commands and notifications</h2>
            </div>
            <span className="pill accent">{dashboard.command_logs?.count || 0} commands</span>
          </div>
          <div className="analytics-grid">
            <div>
              <strong>{dashboard.weather?.temperature_c ?? 0}°C</strong>
              <span>outside temp</span>
            </div>
            <div>
              <strong>{dashboard.weather?.humidity_pct ?? 0}%</strong>
              <span>humidity</span>
            </div>
            <div>
              <strong>{notifications.length}</strong>
              <span>notifications</span>
            </div>
            <div>
              <strong>{lastWorkflow?.command?.action || "-"}</strong>
              <span>last command</span>
            </div>
          </div>
          <div className="stack-list">
            {(dashboard.command_logs?.items || []).slice(-5).reverse().map((item) => (
              <div className="stack-item" key={item.event_id}>
                <div>
                  <p className="stack-title">{item.action}</p>
                  <p className="stack-sub">{item.device_id}</p>
                </div>
                <span>{Number(item.latency_ms).toFixed(0)} ms</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}