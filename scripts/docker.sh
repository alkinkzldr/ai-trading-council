#!/bin/bash

# Helper script for Docker operations

case "$1" in
    up)
        echo "Starting services..."
        docker-compose up -d
        ;;
    down)
        echo "Stopping services..."
        docker-compose down
        ;;
    restart)
        echo "Restarting services..."
        docker-compose down
        docker-compose up -d
        ;;
    clean)
        echo "Stopping and removing volumes..."
        docker-compose down -v
        ;;
    reset)
        echo "Full reset: stopping, removing volumes, and rebuilding..."
        docker-compose down -v --rmi local
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    logs)
        docker-compose logs -f ${2:-}
        ;;
    status)
        docker-compose ps
        ;;
    shell)
        docker-compose exec ${2:-app} bash
        ;;
    test)
        docker-compose exec app pytest tests/ -v
        ;;
    *)
        echo "Usage: $0 {up|down|restart|clean|reset|logs|status|shell|test}"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  clean    - Stop and remove volumes (keeps images)"
        echo "  reset    - Full reset: remove everything and rebuild"
        echo "  logs     - View logs (optionally specify service: logs app)"
        echo "  status   - Show service status"
        echo "  shell    - Open bash in container (default: app)"
        echo "  test     - Run pytest in app container"
        exit 1
        ;;
esac
