#!/bin/bash
# Usage: ./install_framework.sh <framework>
# Framework options: react, nodejs, django, flask

set -e
set -o pipefail
export DEBIAN_FRONTEND=noninteractive

FRAMEWORK=$1

# Function to log with flush
log() { echo "$1"; }

log "Updating system..."
apt update -y | tee /dev/stdout
apt upgrade -y | tee /dev/stdout

log "Installing base packages..."
apt install -y curl git sudo software-properties-common apt-transport-https ca-certificates gnupg lsb-release | tee /dev/stdout

# Install Docker if not present
if ! command -v docker &> /dev/null
then
    log "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh | tee /dev/stdout
    systemctl enable docker
    systemctl start docker
fi

# Install framework dependencies
case $FRAMEWORK in
  react|nodejs)
    log "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - | tee /dev/stdout
    apt install -y nodejs | tee /dev/stdout
    ;;
  django)
    log "Installing Python + Django..."
    apt install -y python3-pip | tee /dev/stdout
    pip3 install django gunicorn --no-cache-dir | tee /dev/stdout
    ;;
  flask)
    log "Installing Python + Flask..."
    apt install -y python3-pip | tee /dev/stdout
    pip3 install flask gunicorn --no-cache-dir | tee /dev/stdout
    ;;
  *)
    log "Framework $FRAMEWORK not supported."
    exit 1
    ;;
esac

log "Framework setup completed!"
