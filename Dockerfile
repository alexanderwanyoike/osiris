# Osiris OS - Phase 2 ISO Builder
FROM debian:trixie

# Install live-build and dependencies
RUN apt-get update && \
    apt-get install -y \
    live-build \
    wget \
    curl \
    gnupg \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /build

# Default command: configure and build with our settings
CMD lb config \
    --architectures amd64 \
    --distribution trixie \
    --archive-areas "main contrib non-free non-free-firmware" \
    --binary-images iso-hybrid \
    --initsystem systemd && \
    lb build