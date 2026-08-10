#!/usr/bin/env bash
#
# PartsDB - run everything with one command.
#
# Builds and starts the full stack (postgres + backend + frontend) via
# Docker Compose, waits for it to come up, and prints access info.
#
# Usage:
#   ./run.sh            build & start in background
#   ./run.sh up         same as above
#   ./run.sh down       stop everything
#   ./run.sh logs       follow container logs
#   ./run.sh rebuild    rebuild images and recreate containers
#   ./run.sh status     show container status
#
set -euo pipefail
cd "$(dirname "$0")"

CMD="${1:-up}"
COMPOSE="docker compose"

case "$CMD" in
  up|start)
    ;&
  rebuild)
    ;&
  *)
    if ! command -v docker >/dev/null 2>&1; then
      echo "ERROR: docker not found. Install Docker first: https://docs.docker.com/engine/install/"
      exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
      echo "ERROR: docker daemon is not running. Start Docker (e.g. open Docker Desktop / systemctl start docker)."
      exit 1
    fi
    ;;
esac

case "$CMD" in
  up|start)
    echo ">> Building and starting PartsDB..."
    $COMPOSE up -d --build
    ;;

  rebuild)
    echo ">> Rebuilding images and recreating containers..."
    $COMPOSE up -d --build --force-recreate
    ;;

  down|stop)
    echo ">> Stopping PartsDB..."
    $COMPOSE down
    exit 0
    ;;

  logs)
    exec $COMPOSE logs -f
    ;;

  status|ps)
    $COMPOSE ps
    exit 0
    ;;

  *)
    echo "Unknown command: $CMD"
    echo "Usage: ./run.sh [up|down|logs|rebuild|status]"
    exit 1
    ;;
esac

echo
echo ">> Waiting for services to be healthy..."
FRONTEND=http://localhost:3000
for i in $(seq 1 60); do
  if curl -sf "$FRONTEND/api/health" >/dev/null 2>&1; then
    echo "   ready after ${i}s"
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "ERROR: PartsDB did not become healthy in 60s. Check logs with: $0 logs"
    $COMPOSE ps
    exit 1
  fi
  sleep 1
done

cat <<'EOF'

PartsDB is running:
  Frontend  : http://localhost:3000
  Backend   : http://localhost:8000   (API docs: http://localhost:8000/docs)
  Database  : postgres on localhost:5432

  Login     : admin / admin
  (customize via .env, see .env.example)

  Stop      : ./run.sh down
  Logs      : ./run.sh logs
EOF
