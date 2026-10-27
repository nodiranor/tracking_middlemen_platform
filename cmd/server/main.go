package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"uztrack/internal/adapters"
	"uztrack/internal/api"
	"uztrack/internal/scheduler"
	"uztrack/internal/storage"
)

func main() {
	log.Println("==================================================================")
	log.Println("  UzTrack (UZ-LTS) - Unified Logistics Clearinghouse for Uzbekistan")
	log.Println("  High-Speed Middleman Gateway for Marketplaces & Couriers")
	log.Println("==================================================================")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	publicDir := os.Getenv("PUBLIC_DIR")
	if publicDir == "" {
		publicDir = "./public"
	}

	// 1. Initialize High-Performance Repository
	repo := storage.NewMemoryRepository()
	log.Println("[Storage] In-memory repository initialized with pre-seeded Uzbekistan hubs & demo routes")

	// 2. Initialize Carrier Adapters
	carrierRegistry := adapters.NewCarrierAdapterRegistry()
	log.Println("[Adapters] Logistics normalization registry loaded (Fargo, BTS, EMU, Yandex, Generic)")

	// 3. Initialize Hourly Tracking Poller
	// For production, runs every 1 hour; during local demo, checks every 30 minutes or on-demand
	pollerInterval := 1 * time.Hour
	poller := scheduler.NewPoller(repo, pollerInterval)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	poller.Start(ctx)

	// 4. Setup HTTP Router & Middleware
	apiHandler := api.NewAPIHandler(repo, carrierRegistry, poller)
	router := api.SetupRouter(apiHandler, publicDir)

	server := &http.Server{
		Addr:         ":" + port,
		Handler:      router,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// 5. Graceful Shutdown Listener
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Printf("[Server] Listening on http://0.0.0.0:%s", port)
		log.Printf("[Server] 3D Tracking Demo: http://localhost:%s/", port)
		log.Printf("[Server] Tracking API: http://localhost:%s/v1/tracks/UZ77019283401", port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[Server Fatal] Listen failed: %v", err)
		}
	}()

	<-stop
	log.Println("[Server] Shutting down gracefully...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()

	poller.Stop()
	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("[Server Error] Shutdown error: %v", err)
	}

	log.Println("[Server] UzTrack platform stopped successfully.")
}
