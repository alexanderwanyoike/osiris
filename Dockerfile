# Osiris OS - Simple ISO Builder
FROM debian:trixie

# Install live-build
RUN apt-get update && apt-get install -y live-build

# Working directory
WORKDIR /build

# Default command: configure and build
CMD lb config --architectures amd64 --distribution trixie --initsystem systemd && lb build