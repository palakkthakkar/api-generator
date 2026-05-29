import React from 'react';
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceDot
} from 'recharts';

interface Props {
  endpoint: string | null;
  data: any[];
}

export function MetricsChart({ endpoint, data }: Props) {
  if (!endpoint) {
    return <div className="empty-state">Select an endpoint to view metrics</div>;
  }

  const filtered = data.filter(d => d.endpoint === endpoint);

  return (
    <div className="charts-container">
      {/* Latency Chart */}
      <div className="chart-card">
        <h3>Latency (ms)</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={filtered}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="latency_p50" stroke="#4ade80" name="p50" dot={false} />
            <Line type="monotone" dataKey="latency_p95" stroke="#facc15" name="p95" dot={false} />
            <Line type="monotone" dataKey="latency_p99" stroke="#f87171" name="p99" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Throughput Chart */}
      <div className="chart-card">
        <h3>Requests / minute</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={filtered}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="request_count" fill="#3b82f6" stroke="#3b82f6" fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Error Rate Chart */}
      <div className="chart-card">
        <h3>Error Rate (%)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={filtered}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
            <Tooltip
              formatter={(v) =>
                typeof v === "number"
                  ? `${(v * 100).toFixed(2)}%`
                  : "0%"
              } />
            <Area type="monotone" dataKey="error_rate" fill="#ef4444" stroke="#ef4444" fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}