#!/bin/bash
# Test script for Feishu plugin via Docker

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Testing Feishu Plugin via Docker ===${NC}"
echo ""

# Check if container is running
if [ ! -z "$1" ] && [ "$1" == "api" ]; then
    echo -e "${YELLOW}Using Apprise API Server...${NC}"

    # Example: Send via API
    # Replace with your actual Feishu URL
    FEISHU_URL="feishu://your_webhook_token_or_app_credentials"

    curl -X POST "http://localhost:8000/notify" \
        -d "urls=${FEISHU_URL}" \
        -d "title=Test from Docker" \
        -d "body=This is a test message sent via Apprise Docker container"

else
    echo -e "${YELLOW}Using Apprise CLI...${NC}"

    # Test 1: Show available plugins
    echo -e "\n${GREEN}Test 1: Checking Feishu plugin...${NC}"
    docker run --rm \
        -v "$(pwd)/config:/config" \
        apprise:latest \
        ls /usr/local/lib/python3.12/site-packages/apprise/plugins/ | grep feishu

    # Test 2: Dry run to validate URL
    echo -e "\n${GREEN}Test 2: Validating Feishu URLs (dry-run)...${NC}"

    echo -e "\n${YELLOW}Testing Webhook Mode URL:${NC}"
    docker run --rm \
        apprise:latest \
        --dry-run \
        --title="Test Title" \
        --body="Test Body" \
        "feishu://test_webhook_token"

    echo -e "\n${YELLOW}Testing App Mode URL:${NC}"
    docker run --rm \
        apprise:latest \
        --dry-run \
        --title="Test Title" \
        --body="Test Body" \
        "feishu://app/cli_test123/secret456/user@example.com"

    # Test 3: Actual notification examples
    echo -e "\n${GREEN}Test 3: Send actual notification (requires real credentials)${NC}"
    echo -e "${RED}Skipping... Uncomment and add your credentials to test${NC}"
    echo ""
    echo "# Example command for Webhook mode:"
    echo "docker run --rm -v \"\$(pwd)/config:/config\" apprise:latest \\"
    echo "  --title=\"Alert\" \\"
    echo "  --body=\"CPU usage 80%\" \\"
    echo "  \"feishu://YOUR_WEBHOOK_TOKEN\""
    echo ""
    echo "# Or using App mode:"
    echo "docker run --rm -v \"\$(pwd)/config:/config\" apprise:latest \\"
    echo "  --title=\"Alert\" \\"
    echo "  --body=\"Server alert\" \\"
    echo "  \"feishu://app/cli_APP_ID/APP_SECRET/user@example.com\""
    echo ""

    # Test 4: Using configuration file
    echo -e "${GREEN}Test 4: Using configuration file${NC}"
    echo -e "${YELLOW}Create a config file at ./config/apprise.conf with your URLs${NC}"
    echo ""
    echo "# Example config/apprise.conf:"
    echo "feishu://YOUR_WEBHOOK_TOKEN"
    echo "feishu://app/cli_APP_ID/APP_SECRET/user1@example.com/user2@example.com"
    echo ""
    echo "# Then run:"
    echo "docker run --rm -v \"\$(pwd)/config:/config\" apprise:latest \\"
    echo "  --config=\"/config/apprise.conf\" \\"
    echo "  --title=\"Test\" \\"
    echo "  --body=\"Message from config file\""
    echo ""
fi

echo -e "${GREEN}=== Tests Complete ===${NC}"
