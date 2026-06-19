import React from 'react';
import DashboardErrorBoundary from '../components/DashboardErrorBoundary';
import { useDashboardStats } from '../hooks';

const statCards = [
  { key: 'totalUsers', label: 'Total Users', color: '#4f46e5' },
  { key: 'activeSessions', label: 'Active Sessions', color: '#059669' },
  { key: 'trialsCompleted', label: 'Trials Completed', color: '#d97706' },
  { key: 'avgResponseTime', label: 'Avg Response Time', color: '#dc2626', suffix: 'ms' },
  { key: 'errorRate', label: 'Error Rate', color: '#7c3aed', suffix: '%' },
  { key: 'uptime', label: 'Uptime', color: '#0891b2', suffix: '%' },
];

type DashboardStats = Record<string, string | number | null | undefined>;

export function normalizeDashboardStats(raw: unknown): DashboardStats {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error('Expected dashboard stats to be an object');
  }

  const stats = raw as DashboardStats;
  for (const card of statCards) {
    const value = stats[card.key];
    if (value === undefined || value === null || value === '') {
      stats[card.key] = ' - ';
      continue;
    }
    if (typeof value !== 'string' && typeof value !== 'number') {
      throw new Error(`Invalid value for ${card.key}`);
    }
  }

  return stats;
}

const DashboardContent: React.FC = () => {
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
      <div className="dashboard-error" role="alert">
        <p>Failed to load dashboard: {(error as Error).message}</p>
      </div>
    );
  }

  const safeStats = normalizeDashboardStats(stats ?? {});

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
                {String(safeStats[card.key])}
                {card.suffix || ''}
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

const Dashboard: React.FC = () => (
  <DashboardErrorBoundary>
    <DashboardContent />
  </DashboardErrorBoundary>
);

export default Dashboard;
