import React, { useState, useEffect } from 'react';

interface EndpointInfo {
  app_name: string;
  endpoint: string;
  latest_p95: number;
  latest_error_rate: number;
  latest_rps: number;
}

interface Props {
  selected: string | null;
  onSelect: (endpoint: string) => void;
}

export function EndpointList({ selected, onSelect }: Props) {
  const [endpoints, setEndpoints] = useState<EndpointInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEndpoints = async () => {
      try {
        const res = await fetch('http://localhost:8100/api/v1/dashboard/endpoints');
        const data = await res.json();
        setEndpoints(data.endpoints || []);
      } catch (err) {
        console.error('Failed to fetch endpoints:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchEndpoints();
    // Refresh every 30 seconds
    const interval = setInterval(fetchEndpoints, 30000);
    return () => clearInterval(interval);
  }, []);

  const getHealthColor = (errorRate: number): string => {
    if (errorRate >= 0.1) return 'var(--accent-red)';
    if (errorRate >= 0.03) return 'var(--accent-yellow)';
    return 'var(--accent-green)';
  };

  const getHealthLabel = (errorRate: number): string => {
    if (errorRate >= 0.1) return 'Critical';
    if (errorRate >= 0.03) return 'Degraded';
    return 'Healthy';
  };

  return (
    <div className="endpoint-list">
      <div className="endpoint-list-header">
        <h2>Endpoints</h2>
        <span className="endpoint-count">{endpoints.length}</span>
      </div>

      {loading && (
        <div className="endpoint-loading">
          <span className="loading-dot" />
          Discovering endpoints...
        </div>
      )}

      {!loading && endpoints.length === 0 && (
        <div className="endpoint-empty">
          No endpoints detected yet. Start sending traffic via the SDK.
        </div>
      )}

      <div className="endpoint-items">
        {endpoints.map((ep) => {
          const key = `${ep.app_name}:${ep.endpoint}`;
          const isSelected = selected === ep.endpoint;
          const healthColor = getHealthColor(ep.latest_error_rate);

          return (
            <button
              key={key}
              className={`endpoint-item ${isSelected ? 'endpoint-item--selected' : ''}`}
              onClick={() => onSelect(ep.endpoint)}
            >
              {/* Health indicator dot */}
              <span
                className="health-dot"
                style={{ backgroundColor: healthColor }}
                title={getHealthLabel(ep.latest_error_rate)}
              />

              <div className="endpoint-item-content">
                <div className="endpoint-path">{ep.endpoint}</div>
                <div className="endpoint-meta">
                  <span className="endpoint-app">{ep.app_name}</span>
                </div>
                <div className="endpoint-stats">
                  <span className="stat">
                    <span className="stat-label">p95</span>
                    <span className="stat-value">{ep.latest_p95.toFixed(0)}ms</span>
                  </span>
                  <span className="stat">
                    <span className="stat-label">err</span>
                    <span
                      className="stat-value"
                      style={{ color: healthColor }}
                    >
                      {(ep.latest_error_rate * 100).toFixed(1)}%
                    </span>
                  </span>
                  <span className="stat">
                    <span className="stat-label">rps</span>
                    <span className="stat-value">{ep.latest_rps}</span>
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
