import React from 'react';

type DashboardErrorBoundaryProps = {
  children: React.ReactNode;
};

type DashboardErrorBoundaryState = {
  hasError: boolean;
  message: string;
};

class DashboardErrorBoundary extends React.Component<
  DashboardErrorBoundaryProps,
  DashboardErrorBoundaryState
> {
  state: DashboardErrorBoundaryState = {
    hasError: false,
    message: '',
  };

  static getDerivedStateFromError(error: Error): DashboardErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || 'Unexpected dashboard data error',
    };
  }

  componentDidCatch(error: Error): void {
    // Keep the UI recoverable without dumping raw diagnostic payloads or secrets.
    console.error('Dashboard rendering failed:', error.message);
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="dashboard-error" role="alert">
          <p>Dashboard data is malformed and could not be rendered safely.</p>
          <p className="dashboard-error-detail">{this.state.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default DashboardErrorBoundary;
