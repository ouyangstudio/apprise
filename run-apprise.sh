#!/bin/bash
# Apprise Docker Run Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Apprise Docker Runner ===${NC}"

# Function to show usage
usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  server      Run Apprise API server on port 8000"
    echo "  test        Test Apprise CLI"
    echo "  shell       Open shell in container"
    echo "  logs        Show container logs"
    echo "  stop        Stop running containers"
    echo "  clean       Remove containers and images"
    echo ""
    echo "Examples:"
    echo "  $0 server"
    echo "  $0 test --help"
    echo "  $0 shell"
}

# Check if command is provided
if [ -z "$1" ]; then
    usage
    exit 1
fi

COMMAND=$1
shift

case "$COMMAND" in
    server)
        echo -e "${GREEN}Starting Apprise API server...${NC}"
        echo -e "URL will be: ${YELLOW}http://localhost:8000${NC}"
        docker run -d \
            --name apprise-server \
            --restart unless-stopped \
            -p 8000:8000 \
            -v "$(pwd)/config:/config" \
            -e APPRISE_LOG_LEVEL=info \
            apprise:latest \
            --verbose --config="/config/apprise.conf" --server="0.0.0.0:8000"
        echo -e "${GREEN}Server started!${NC}"
        echo "Check logs with: $0 logs"
        echo "Stop with: $0 stop"
        ;;

    test)
        echo -e "${GREEN}Running Apprise CLI in test mode...${NC}"
        docker run -it --rm \
            -v "$(pwd)/config:/config" \
            apprise:latest \
            "$@"
        ;;

    shell)
        echo -e "${GREEN}Opening shell in container...${NC}"
        docker run -it --rm \
            -v "$(pwd)/config:/config" \
            --entrypoint /bin/bash \
            apprise:latest
        ;;

    logs)
        if docker ps | grep -q apprise-server; then
            echo -e "${GREEN}Showing logs from apprise-server:${NC}"
            docker logs -f apprise-server
        else
            echo -e "${RED}No running apprise-server container found${NC}"
            exit 1
        fi
        ;;

    stop)
        echo -e "${YELLOW}Stopping apprise-server...${NC}"
        docker stop apprise-server 2>/dev/null
        docker rm apprise-server 2>/dev/null
        echo -e "${GREEN}Server stopped${NC}"
        ;;

    clean)
        echo -e "${YELLOW}Cleaning up...${NC}"
        docker stop apprise-server 2>/dev/null
        docker rm apprise-server 2>/dev/null
        docker rmi apprise:latest 2>/dev/null
        echo -e "${GREEN}Cleanup complete${NC}"
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        exit 1
        ;;
esac
