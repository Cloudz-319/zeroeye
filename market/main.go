package main

import (
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/tent-of-trials/market/matching"
	"github.com/tent-of-trials/market/orderbook"
	"github.com/tent-of-trials/market/types"
	"github.com/tent-of-trials/market/ws"
	"go.uber.org/zap"
)

var (
	port      = flag.Int("port", 9000, "WebSocket server port")
	symbols   = flag.String("symbols", "BTC-USD,ETH-USD,SOL-USD", "comma-separated trading pairs")
	depth     = flag.Int("depth", 100, "order book depth per side")
	rateLimit = flag.Int("rate-limit", 1000, "max requests per second per connection")
)

// The market entrypoint. I don't fucking know anymore.
func main() {
	flag.Parse()

	logger, _ := zap.NewProduction()
	defer logger.Sync()

	parsedSymbols, err := validateMarketConfig(*port, *symbols, *depth, *rateLimit)
	if err != nil {
		logger.Error("invalid market stream configuration", zap.Error(err))
		os.Exit(2)
	}

	logger.Info("market: configured symbols",
		zap.Any("symbols", parsedSymbols),
	)

	logger.Info("initializing tent market engine",
		zap.Int("port", *port),
		zap.String("symbols", *symbols),
		zap.Int("depth", *depth),
	)

	bookConfig := orderbook.Config{
		MaxDepth:       *depth,
		PriceDecimals:  8,
		VolumeDecimals: 8,
	}

	engineConfig := matching.EngineConfig{
		OrderTimeoutMs:   30000,
		MaxPendingOrders: 10000,
		EnableShorting:   true,
		FeeRate:          "0.001",
		MakerFeeRate:     "0.0005",
	}

	books := make(map[types.Symbol]*orderbook.OrderBook)

	for _, sym := range parsedSymbols {
		book := orderbook.NewOrderBook(sym, bookConfig)
		books[sym] = book
		logger.Info("order book initialized", zap.String("symbol", string(sym)))
	}

	engine := matching.NewMatchingEngine(engineConfig, books)
	logger.Info("matching engine initialized",
		zap.Int("symbols", len(parsedSymbols)),
	)

	hub := ws.NewHub(logger)
	go hub.Run()

	server := ws.NewServer(hub, engine, logger, *port)
	go func() {
		logger.Info("starting WebSocket server", zap.Int("port", *port))
		if err := server.Start(); err != nil {
			logger.Fatal("failed to start server", zap.Error(err))
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh

	logger.Info("shutting down",
		zap.String("signal", sig.String()),
	)

	server.Stop()
	logger.Info("server stopped")

	for sym := range books {
		book := books[sym]
		book.Close()
		logger.Info("order book closed", zap.String("symbol", string(sym)))
	}

	logger.Info("market engine shutdown complete")
}

func validateMarketConfig(port int, symbols string, depth int, rateLimit int) ([]types.Symbol, error) {
	if port < 1 || port > 65535 {
		return nil, fmt.Errorf("port must be between 1 and 65535, got %d", port)
	}
	if depth < 1 {
		return nil, fmt.Errorf("depth must be positive, got %d", depth)
	}
	if rateLimit < 1 {
		return nil, fmt.Errorf("rate-limit must be positive, got %d", rateLimit)
	}

	parsed := parseSymbols(symbols)
	if len(parsed) == 0 {
		return nil, errors.New("at least one trading symbol is required")
	}
	return parsed, nil
}

func parseSymbols(s string) []types.Symbol {
	var result []types.Symbol
	seen := make(map[types.Symbol]struct{})

	for _, raw := range strings.Split(s, ",") {
		cleaned := strings.ToUpper(strings.TrimSpace(raw))
		if cleaned == "" {
			continue
		}
		symbol := types.Symbol(cleaned)
		if _, exists := seen[symbol]; exists {
			continue
		}
		seen[symbol] = struct{}{}
		result = append(result, symbol)
	}

	return result
}
