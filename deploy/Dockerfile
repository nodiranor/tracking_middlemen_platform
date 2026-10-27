# ==============================================================================
# UzTrack (UZ-LTS) - Multi-Stage High-Speed Container Build
# Target Size: ~18MB | Base: Alpine Linux | Extreme Concurrency
# ==============================================================================

# Stage 1: Build the Go binary
FROM golang:1.22-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git ca-certificates tzdata

COPY go.mod ./
# If go.sum exists, copy it
COPY go.mod go.sum* ./
RUN go mod download || true

COPY . .

# Compile statically linked binary with stripped debug symbols (-s -w)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-s -w -X main.version=1.0.0" \
    -o /app/uztrack-server ./cmd/server/main.go

# Stage 2: Final Minimal Runtime Image
FROM alpine:3.19

WORKDIR /app

RUN apk --no-cache add ca-certificates tzdata
ENV TZ=Asia/Tashkent

COPY --from=builder /app/uztrack-server /app/uztrack-server
COPY public /app/public

EXPOSE 8080

ENTRYPOINT ["/app/uztrack-server"]
