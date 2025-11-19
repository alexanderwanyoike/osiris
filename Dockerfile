# check=skip=JSONArgsRecommended
# Osiris OS - ISO Builder (Live + Installer Support)
FROM debian:trixie

# Install live-build and all dependencies (including installer tools)
RUN apt-get update && \
    apt-get install -y \
    live-build \
    wget \
    curl \
    gnupg \
    ca-certificates \
    xorriso \
    isolinux \
    syslinux-common && \
    rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /build

# Default command: configure and build with installer support
CMD lb config \
    --architectures amd64 \
    --distribution trixie \
    --archive-areas "main contrib non-free non-free-firmware" \
    --binary-images iso-hybrid \
    --initsystem systemd \
    --debian-installer live \
    --debian-installer-gui true \
    --debian-installer-distribution trixie \
    --bootappend-live "boot=live components quiet splash" \
    --apt-indices false \
    --apt-recommends false && \
    lb build