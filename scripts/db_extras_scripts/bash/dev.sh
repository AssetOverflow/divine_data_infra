#!/bin/bash
# dev.sh — orchestrates build, volume copy, and stack launch

set -e

STACK_NAME=${STACK_NAME:-divinehaven-backend}
COMPOSE_FILE=../../../docker-compose.backend.yml
COPY_SCRIPT=scripts/db_extras_scripts/bash/copy_volumes.sh

echo "🔧 Building containers for $STACK_NAME..."
docker-compose -f $COMPOSE_FILE build

echo "📦 Copying volumes from guided build to data infra..."
bash $COPY_SCRIPT

echo "🚀 Launching $STACK_NAME stack..."
docker-compose -f $COMPOSE_FILE up -d

echo "✅ Stack is live. Use 'make logs' or 'docker ps' to monitor."