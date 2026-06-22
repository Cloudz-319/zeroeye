# Fix for Issue #3: [$25 BOUNTY] [Go] Validate market stream configuration before startup

package market

import (
	"os"
	"testing"
	"time"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg.Host != "0.0.0.0" {
		t.Errorf("expected default host 0.0.0.0, got %s", cfg.Host)
	}
	if cfg.Port != 8080 {
		t.Errorf("expected default port 8080, got %d", cfg.Port)
	}
	if cfg.ReconnectDelay != 5*time.Second {
		t.Errorf("expected default reconnect delay 5s, got %v", cfg.ReconnectDelay)
	}
	if cfg.MaxReconnects != 10 {
		t.Errorf("expected default max reconnects 10, got %d", cfg.MaxReconnects)
	}
}

func TestLoadFromEnv(t *testing.T) {
	// Clean up env vars after test
	defer func() {
		os.Unsetenv("MARKET_WS_HOST")
		os.Unsetenv("MARKET_WS_PORT")
		os.Unsetenv("MARKET_STREAM_URL")
		os.Unsetenv("MARKET_RECONNECT_DELAY")
		os.Unsetenv("MARKET_MAX_RECONNECTS")
	}()

	// Set valid configuration
	os.Setenv("MARKET_WS_HOST", "127.0.0.1")
	os.Setenv("MARKET_WS_PORT", "9000")
	os.Setenv("MARKET_STREAM_URL", "wss://stream.example.com/ws")
	os.Setenv("MARKET_RECONNECT_DELAY", "10s")
	os.Setenv("MARKET_MAX_RECONNECTS", "5")

	cfg, err := LoadFromEnv()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.Host != "127.0.0.1" {
		t.Errorf("expected host 127.0.0.1, got %s", cfg.Host)
	}
	if cfg.Port != 9000 {
		t.Errorf("expected port 9000, got %d", cfg.Port)
	}
	if cfg.StreamURL != "wss://stream.example.com/ws" {
		t.Errorf("expected stream URL wss://stream.example.com/ws, got %s", cfg.StreamURL)
	}
	if cfg.ReconnectDelay != 10*time.Second {
		t.Errorf("expected reconnect delay 10s, got %v", cfg.ReconnectDelay)
	}
	if cfg.MaxReconnects != 5 {
		t.Errorf("expected max reconnects 5, got %d", cfg.MaxReconnects)
	}
}

func TestLoadFromEnv_InvalidPort(t *testing.T) {
	defer os.Unsetenv("MARKET_WS_PORT")

	os.Setenv("MARKET_WS_PORT", "invalid")

	_, err := LoadFromEnv()
	if err == nil {
		t.Fatal("expected error for invalid port, got nil")
	}
}

func TestLoadFromEnv_InvalidDuration(t *testing.T) {
	defer os.Unsetenv("MARKET_RECONNECT_DELAY")

	os.Setenv("MARKET_RECONNECT_DELAY", "not-a-duration")

	_, err := LoadFromEnv()
	if err == nil {
		t.Fatal("expected error for invalid duration, got nil")
	}
}