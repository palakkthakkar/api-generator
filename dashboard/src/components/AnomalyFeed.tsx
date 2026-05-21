import React from 'react';

interface FeatureContribution {
  feature: string;
  deviation: number;
}

interface AnomalyEvent {
  id?: number;
  endpoint: string;
  app_name: string;
  detected_at: string;
  severity: number;
  score: number;
  features: FeatureContribution[];
}

interface Props {
  anomalies: AnomalyEvent[];
}

export function AnomalyFeed({ anomalies }: Props) {
  const getSeverityLevel = (severity: number) => {
    if (severity >= 0.7) return { label: 'Critical', className: 'severity--critical' };
    if (severity >= 0.4) return { label: 'Warning', className: 'severity--warning' };
    return { label: 'Info', className: 'severity--info' };
  };

  const formatTime = (iso: string): string => {
    try {
      const date = new Date(iso);
      return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  const formatFeatureName = (name: string): string => {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
      .replace('P50', 'p50')
      .replace('P95', 'p95')
      .replace('P99', 'p99')
      .replace('Avg ', 'Avg. ')
      .replace('Std', 'StdDev');
  };

  return (
    <div className="anomaly-feed">
      <div className="anomaly-feed-header">
        <h2>Anomalies</h2>
        {anomalies.length > 0 && (
          <span className="anomaly-count anomaly-count--active">
            {anomalies.length}
          </span>
        )}
      </div>

      {anomalies.length === 0 && (
        <div className="anomaly-empty">
          <div className="anomaly-empty-icon">✓</div>
          <p>No anomalies detected</p>
          <span>All endpoints operating normally</span>
        </div>
      )}

      <div className="anomaly-items">
        {anomalies.map((anomaly, index) => {
          const { label, className } = getSeverityLevel(anomaly.severity);

          return (
            <div
              key={anomaly.id || index}
              className={`anomaly-card ${className}`}
              style={{
                animationDelay: `${index * 0.05}s`,
              }}
            >
              {/* Header row: severity badge + time */}
              <div className="anomaly-card-header">
                <span className={`severity-badge ${className}`}>
                  {label} — {(anomaly.severity * 100).toFixed(0)}%
                </span>
                <span className="anomaly-time">
                  {formatTime(anomaly.detected_at)}
                </span>
              </div>

              {/* Endpoint */}
              <div className="anomaly-endpoint">{anomaly.endpoint}</div>

              {/* Score */}
              <div className="anomaly-score">
                Score: {anomaly.score.toFixed(4)}
              </div>

              {/* Contributing features */}
              {anomaly.features && anomaly.features.length > 0 && (
                <div className="anomaly-features">
                  <span className="features-label">Top deviations:</span>
                  {anomaly.features.slice(0, 3).map((f, i) => (
                    <div key={i} className="feature-row">
                      <span className="feature-name">
                        {formatFeatureName(f.feature)}
                      </span>
                      <div className="feature-bar-container">
                        <div
                          className="feature-bar"
                          style={{
                            width: `${Math.min(f.deviation * 100, 100)}%`,
                          }}
                        />
                      </div>
                      <span className="feature-value">
                        {f.deviation.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
