import React, { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { EndpointList } from './components/EndpointList';
import { MetricsChart } from './components/MetricsChart';
import { AnomalyFeed } from './components/AnomalyFeed';
import './App.css';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8100/ws/dashboard';

function App() {
  const { lastMessage, isConnected } = useWebSocket(WS_URL);
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);

  // Process incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.channel.startsWith('metrics:')) {
      setMetricsHistory((prev) => {
        const updated = [...prev, lastMessage.data];
        // Keep last 120 data points (~2 hours at 1-min windows)
        if (updated.length > 120) {
          return updated.slice(updated.length - 120);
        }
        return updated;
      });
    }

    if (lastMessage.channel.startsWith('anomaly:')) {
      setAnomalies((prev) => {
        const updated = [lastMessage.data, ...prev];
        // Keep last 50 anomalies
        if (updated.length > 50) {
          return updated.slice(0, 50);
        }
        return updated;
      });
    }
  }, [lastMessage]);

  // Also fetch historical anomalies on mount
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch('http://localhost:8100/api/v1/dashboard/anomalies?hours=24');
        const data = await res.json();
        if (data.anomalies) {
          setAnomalies(data.anomalies);
        }
      } catch (err) {
        console.error('Failed to fetch anomaly history:', err);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <div className="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <h1>SentinelAPI</h1>
          </div>
          <span className="header-version">v0.1.0</span>
        </div>
        <div className="header-right">
          <div className={`connection-status ${isConnected ? 'status--connected' : 'status--disconnected'}`}>
            <span className="status-dot" />
            <span className="status-label">
              {isConnected ? 'Live' : 'Reconnecting...'}
            </span>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="dashboard-layout">
        {/* Left sidebar: Endpoints */}
        <aside className="sidebar-left">
          <EndpointList
            selected={selectedEndpoint}
            onSelect={setSelectedEndpoint}
          />
        </aside>

        {/* Center: Charts */}
        <main className="main-content">
          <MetricsChart
            endpoint={selectedEndpoint}
            data={metricsHistory}
          />
        </main>

        {/* Right sidebar: Anomaly feed */}
        <aside className="sidebar-right">
          <AnomalyFeed anomalies={anomalies} />
        </aside>
      </div>
    </div>
  );
}

export default App;
