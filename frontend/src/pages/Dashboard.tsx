import React from 'react';
import { useDashboardStats } from '../hooks';
import type { DashboardStats } from '../types';

const statCards = [
  { key: 'totalUsers', label: 'Total Users', color: '#4f46e5', suffix: '' },
  { key: 'activeSessions', label: 'Active Sessions', color: '#059669', suffix: '' },
  { key: 'trialsCompleted', label: 'Trials Completed', color: '#d97706', suffix: '' },
  { key: 'avgResponseTime', label: 'Avg Response Time', color: '#dc2626', suffix: 'ms' },
  { key: 'errorRate', label: 'Error Rate', color: '#7c3aed', suffix: '%' },
  { key: 'uptime', label: 'Uptime', color: '#0891b2', suffix: '%' },
] as const;

type StatKey = (typeof statCards)[number]['key'];

const requiredStatKeys: StatKey[] = statCards.map((card) => card.key);

function isDashboardStatsPayload(value: unknown): value is DashboardStats {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const payload = value as Record<string, unknown>;
  return requiredStatKeys.every((key) => (
    typeof payload[key] === 'number' && Number.isFinite(payload[key])
  ));
}

const Dashboard: React.FC = () => {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner" />
        <p>Loading dashboard data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <p>Failed to load dashboard: {(error as Error).message}</p>
      </div>
    );
  }

  if (!isDashboardStatsPayload(stats)) {
    return (
      <div className="dashboard-error" role="alert">
        <p>Dashboard diagnostics are unavailable because the payload is malformed.</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <p className="dashboard-subtitle">
          Tent of Trials System Overview
        </p>
      </div>

      <div className="stats-grid">
        {statCards.map((card) => (
          <div key={card.key} className="stat-card">
            <div
              className="stat-card-indicator"
              style={{ backgroundColor: card.color }}
            />
            <div className="stat-card-content">
              <span className="stat-card-label">{card.label}</span>
              <span
                className="stat-card-value"
                style={{ color: card.color }}
              >
                {String(stats[card.key])}
                {card.suffix}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-panels">
        <div className="panel">
          <h3>Recent Activity</h3>
          <div className="panel-placeholder">
            Activity feed will appear here
          </div>
        </div>
        <div className="panel">
          <h3>System Health</h3>
          <div className="panel-placeholder">
            Health metrics will appear here
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
