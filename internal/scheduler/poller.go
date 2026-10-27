package scheduler

import (
	"context"
	"fmt"
	"log"
	"time"

	"uztrack/internal/domain"
	"uztrack/internal/storage"
)

// Poller manages periodic hourly tracking updates and waypoint progress.
type Poller struct {
	repo     storage.Repository
	interval time.Duration
	stopChan chan struct{}
}

// NewPoller creates an hourly background scheduler.
func NewPoller(repo storage.Repository, interval time.Duration) *Poller {
	if interval <= 0 {
		interval = 1 * time.Hour
	}
	return &Poller{
		repo:     repo,
		interval: interval,
		stopChan: make(chan struct{}),
	}
}

// Start launches the hourly tracking loop in a goroutine.
func (p *Poller) Start(ctx context.Context) {
	log.Printf("[UzTrack Scheduler] Starting hourly tracking poller with interval: %v", p.interval)
	ticker := time.NewTicker(p.interval)

	go func() {
		for {
			select {
			case <-ticker.C:
				p.ExecuteHourlyUpdate()
			case <-p.stopChan:
				ticker.Stop()
				return
			case <-ctx.Done():
				ticker.Stop()
				return
			}
		}
	}()
}

// Stop cleanly terminates the poller.
func (p *Poller) Stop() {
	close(p.stopChan)
}

// ExecuteHourlyUpdate checks all active in-transit shipments and advances hourly checkpoints.
func (p *Poller) ExecuteHourlyUpdate() {
	active, err := p.repo.ListActiveShipments()
	if err != nil {
		log.Printf("[UzTrack Scheduler Error] Failed to list active shipments: %v", err)
		return
	}

	now := time.Now().UTC()
	log.Printf("[UzTrack Scheduler] Running hourly checkpoint refresh for %d active shipments at %s", len(active), now.Format(time.RFC3339))

	for _, s := range active {
		if s.Status == domain.StatusInTransit {
			p.interpolateNextWaypoint(s, now)
		}
	}
}

// interpolateNextWaypoint updates the simulated position along waypoints during intercity transit.
func (p *Poller) interpolateNextWaypoint(s *domain.Shipment, now time.Time) {
	waypoints := s.Route.Waypoints
	if len(waypoints) == 0 {
		return
	}

	// Find the next unpassed waypoint
	for i := range waypoints {
		if !waypoints[i].IsPassed {
			// Mark this waypoint as passed
			waypoints[i].IsPassed = true
			waypoints[i].PassedAt = &now

			// Update current location
			s.CurrentLocation = domain.Location{
				City:      waypoints[i].City,
				Hub:       waypoints[i].Label,
				Lat:       waypoints[i].Lat,
				Lng:       waypoints[i].Lng,
				UpdatedAt: now,
			}

			// If it's the last waypoint, transition to DEST_HUB_IN
			var newStatus domain.ShipmentStatus
			if i == len(waypoints)-1 {
				newStatus = domain.StatusDestHubIn
			} else {
				newStatus = domain.StatusInTransit
			}

			note := fmt.Sprintf("Soatlik nazorat: Jo'natma %s (%s) nazorat nuqtasidan muvaffaqiyatli o'tdi.", waypoints[i].City, waypoints[i].Label)
			_, err := p.repo.UpdateShipmentStatus(s.TrackingCode, newStatus, s.CurrentLocation, note)
			if err != nil {
				log.Printf("[UzTrack Scheduler] Error updating status for %s: %v", s.TrackingCode, err)
			} else {
				log.Printf("[UzTrack Scheduler] Updated %s to checkpoint '%s' (%s)", s.TrackingCode, waypoints[i].Label, waypoints[i].City)
			}
			return
		}
	}
}

// SimulateOneHourStep allows instant demonstration of the hourly progress update.
func (p *Poller) SimulateOneHourStep(trackingCode string) (*domain.Shipment, error) {
	s, err := p.repo.GetShipmentByTrackingCode(trackingCode)
	if err != nil {
		return nil, err
	}

	p.interpolateNextWaypoint(s, time.Now().UTC())
	return p.repo.GetShipmentByTrackingCode(trackingCode)
}
