package main

import (
	"reflect"
	"testing"

	"github.com/tent-of-trials/market/types"
)

func TestParseSymbolsNormalizesTrimsAndDeduplicates(t *testing.T) {
	got := parseSymbols(" btc-usd, ETH-USD,,btc-usd , sol-usd ")
	want := []types.Symbol{"BTC-USD", "ETH-USD", "SOL-USD"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("parseSymbols() = %#v, want %#v", got, want)
	}
}

func TestValidateMarketConfigRejectsInvalidInputs(t *testing.T) {
	cases := []struct {
		name      string
		port      int
		symbols   string
		depth     int
		rateLimit int
	}{
		{"low port", 0, "BTC-USD", 10, 100},
		{"high port", 70000, "BTC-USD", 10, 100},
		{"empty symbols", 9000, " , ", 10, 100},
		{"zero depth", 9000, "BTC-USD", 0, 100},
		{"zero rate limit", 9000, "BTC-USD", 10, 0},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := validateMarketConfig(tc.port, tc.symbols, tc.depth, tc.rateLimit); err == nil {
				t.Fatalf("expected validation error")
			}
		})
	}
}

func TestValidateMarketConfigAcceptsValidConfig(t *testing.T) {
	got, err := validateMarketConfig(9000, "btc-usd,eth-usd", 100, 1000)
	if err != nil {
		t.Fatalf("unexpected validation error: %v", err)
	}
	want := []types.Symbol{"BTC-USD", "ETH-USD"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("validateMarketConfig() symbols = %#v, want %#v", got, want)
	}
}
