package api

import (
	"log"
	"net/http"
	"strings"
	"time"
)

// SetupRouter registers all HTTP routes and static file handlers with CORS and logging.
func SetupRouter(handler *APIHandler, publicDir string) http.Handler {
	mux := http.NewServeMux()

	// API Endpoints
	mux.HandleFunc("/v1/tracks/", func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "/simulate-hour") {
			handler.HandleSimulateHour(w, r)
			return
		}
		if r.Method == http.MethodGet {
			handler.HandleGetTracking(w, r)
			return
		}
		ErrorResponse(w, http.StatusMethodNotAllowed, "Method not allowed")
	})

	mux.HandleFunc("/v1/shipments", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			handler.HandleCreateShipment(w, r)
			return
		}
		ErrorResponse(w, http.StatusMethodNotAllowed, "Method not allowed")
	})

	mux.HandleFunc("/v1/carriers", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			handler.HandleListCarriers(w, r)
			return
		}
		ErrorResponse(w, http.StatusMethodNotAllowed, "Method not allowed")
	})

	mux.HandleFunc("/v1/carriers/", func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "/webhook") && r.Method == http.MethodPost {
			handler.HandleCarrierWebhook(w, r)
			return
		}
		ErrorResponse(w, http.StatusNotFound, "Endpoint not found")
	})

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		JSONResponse(w, http.StatusOK, map[string]interface{}{
			"status":    "healthy",
			"timestamp": time.Now().UTC(),
			"platform":  "UzTrack (UZ-LTS) Gateway",
		})
	})

	// Static frontend file server (HTML, widget.js, CSS, 3D assets)
	fileServer := http.FileServer(http.Dir(publicDir))
	mux.Handle("/", fileServer)

	// Wrap with Global Middleware (CORS & Logging)
	return withCORS(withLogging(mux))
}

// withCORS adds open cross-origin headers so marketplaces can embed the 3D widget.
func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, X-Marketplace-ID")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// withLogging logs request methods, paths, and durations.
func withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		if strings.HasPrefix(r.URL.Path, "/v1/") || r.URL.Path == "/health" {
			log.Printf("[HTTP] %s %s from %s in %v", r.Method, r.URL.Path, r.RemoteAddr, time.Since(start))
		}
	})
}
