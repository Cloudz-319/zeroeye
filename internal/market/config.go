# Fix for Issue #3: [$25 BOUNTY] [Go] Validate market stream configuration before startup

package market

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config holds the market stream WebSocket service configuration
type Config struct {
	// WebSocket server settings
	Host string
	Port int

	// Market stream settings
	StreamURL        string
	ReconnectDelay   time.Duration
	MaxReconnects    int
	PingInterval     time.Duration
	PongTimeout      time.Duration
	WriteBufferSize  int
	ReadBufferSize   int

	// Authentication
	APIKey    string
	APISecret string

	// Feature flags
	EnableCompression bool
	EnableMetrics     bool
	MetricsPort       int
}

// DefaultConfig returns a Config with sensible defaults
func DefaultConfig() *Config {
	return &Config{
		Host:             "0.0.0.0",
		Port:             8080,
		ReconnectDelay:   5 * time.Second,
		MaxReconnects:    10,
		PingInterval:     30 * time.Second,
		PongTimeout:      10 * time.Second,
		WriteBufferSize:  1024,
		ReadBufferSize:   1024,
		EnableCompression: false,
		EnableMetrics:    true,
		MetricsPort:      9090,
	}
}

// LoadFromEnv loads configuration from environment variables, applying defaults where appropriate
func LoadFromEnv() (*Config, error) {
	cfg := DefaultConfig()

	// Host - optional with default
	if host := os.Getenv("MARKET_WS_HOST"); host != "" {
		cfg.Host = host
	}

	// Port - optional with default
	if portStr := os.Getenv("MARKET_WS_PORT"); portStr != "" {
		port, err := strconv.Atoi(portStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_WS_PORT: %w", err)
		}
		cfg.Port = port
	}

	// StreamURL - required
	cfg.StreamURL = os.Getenv("MARKET_STREAM_URL")

	// ReconnectDelay - optional with default
	if delayStr := os.Getenv("MARKET_RECONNECT_DELAY"); delayStr != "" {
		delay, err := time.ParseDuration(delayStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_RECONNECT_DELAY: %w", err)
		}
		cfg.ReconnectDelay = delay
	}

	// MaxReconnects - optional with default
	if maxStr := os.Getenv("MARKET_MAX_RECONNECTS"); maxStr != "" {
		max, err := strconv.Atoi(maxStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_MAX_RECONNECTS: %w", err)
		}
		cfg.MaxReconnects = max
	}

	// PingInterval - optional with default
	if pingStr := os.Getenv("MARKET_PING_INTERVAL"); pingStr != "" {
		ping, err := time.ParseDuration(pingStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_PING_INTERVAL: %w", err)
		}
		cfg.PingInterval = ping
	}

	// PongTimeout - optional with default
	if pongStr := os.Getenv("MARKET_PONG_TIMEOUT"); pongStr != "" {
		pong, err := time.ParseDuration(pongStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_PONG_TIMEOUT: %w", err)
		}
		cfg.PongTimeout = pong
	}

	// WriteBufferSize - optional with default
	if wbsStr := os.Getenv("MARKET_WRITE_BUFFER_SIZE"); wbsStr != "" {
		wbs, err := strconv.Atoi(wbsStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_WRITE_BUFFER_SIZE: %w", err)
		}
		cfg.WriteBufferSize = wbs
	}

	// ReadBufferSize - optional with default
	if rbsStr := os.Getenv("MARKET_READ_BUFFER_SIZE"); rbsStr != "" {
		rbs, err := strconv.Atoi(rbsStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_READ_BUFFER_SIZE: %w", err)
		}
		cfg.ReadBufferSize = rbs
	}

	// APIKey - required for authenticated streams
	cfg.APIKey = os.Getenv("MARKET_API_KEY")

	// APISecret - required for authenticated streams
	cfg.APISecret = os.Getenv("MARKET_API_SECRET")

	// EnableCompression - optional with default
	if compStr := os.Getenv("MARKET_ENABLE_COMPRESSION"); compStr != "" {
		comp, err := strconv.ParseBool(compStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_ENABLE_COMPRESSION: %w", err)
		}
		cfg.EnableCompression = comp
	}

	// EnableMetrics - optional with default
	if metricsStr := os.Getenv("MARKET_ENABLE_METRICS"); metricsStr != "" {
		metrics, err := strconv.ParseBool(metricsStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_ENABLE_METRICS: %w", err)
		}
		cfg.EnableMetrics = metrics
	}

	// MetricsPort - optional with default
	if mpStr := os.Getenv("MARKET_METRICS_PORT"); mpStr != "" {
		mp, err := strconv.Atoi(mpStr)
		if err != nil {
			return nil, fmt.Errorf("invalid MARKET_METRICS_PORT: %w", err)
		}
		cfg.MetricsPort = mp
	}

	return cfg, nil
}