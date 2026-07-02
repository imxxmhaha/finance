#!/bin/bash
set -e

SERVICE="customer-service"

echo "==> Pulling latest code..."
git pull

echo "==> Stopping and removing old containers..."
docker compose down -v $SERVICE

echo "==> Building and starting $SERVICE..."
docker compose up -d --build $SERVICE

echo "==> Done! $SERVICE is running."
