#!/bin/bash
set -e

SERVICE="customer-service"
FRONTEND="frontend"
MIDDLEWARE="finance-data"

# 默认只部署客服服务，可通过参数添加其他服务
SERVICES="$SERVICE"

for arg in "$@"; do
    case $arg in
        --frontend|-f)
            SERVICES="$SERVICES $FRONTEND"
            ;;
        --middleware|-m)
            SERVICES="$SERVICES $MIDDLEWARE"
            ;;
        --all|-a)
            SERVICES="$SERVICE $FRONTEND $MIDDLEWARE"
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--frontend|-f] [--middleware|-m] [--all|-a]"
            echo "  --frontend, -f    Include frontend service"
            echo "  --middleware, -m  Include finance-data middleware service"
            echo "  --all, -a         Include all services"
            exit 1
            ;;
    esac
done

echo "==> Pulling latest code..."
git pull

echo "==> Stopping and removing old containers..."
docker compose down -v $SERVICES

echo "==> Building and starting: $SERVICES..."
docker compose up -d --build $SERVICES

echo "==> Done! Services running: $SERVICES"
