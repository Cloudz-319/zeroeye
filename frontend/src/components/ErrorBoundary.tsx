import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          style={{
            padding: '24px',
            margin: '16px 0',
            borderRadius: '8px',
            backgroundColor: '#1a1a2e',
            border: '1px solid #e94560',
            color: '#e2e8f0',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          }}
        >
          <h3 style={{ margin: '0 0 8px 0', color: '#e94560', fontSize: '1.1em' }}>
            Something went wrong
          </h3>
          <p style={{ margin: '0 0 12px 0', color: '#94a3b8', fontSize: '0.9em' }}>
            The dashboard encountered an unexpected error while rendering diagnostic data.
            This is usually caused by malformed or missing data fields.
          </p>
          <details style={{ marginTop: '8px' }}>
            <summary style={{ cursor: 'pointer', color: '#64748b', fontSize: '0.85em' }}>
              Error details
            </summary>
            <pre
              style={{
                marginTop: '8px',
                padding: '12px',
                backgroundColor: '#0f172a',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '0.8em',
                color: '#94a3b8',
              }}
            >
              {this.state.error?.message || 'Unknown error'}
            </pre>
          </details>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              marginTop: '12px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid #30363d',
              backgroundColor: '#21262d',
              color: '#58a6ff',
              cursor: 'pointer',
              fontSize: '0.85em',
            }}
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
