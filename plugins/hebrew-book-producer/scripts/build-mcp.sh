#!/usr/bin/env bash
# hebrew-book-producer — Gemini MCP Server Build
# Builds the bundled MCP server at plugins/hebrew-book-producer/mcp/gemini-server/
#
# Run from the plugin directory or with the absolute path:
#   bash plugins/hebrew-book-producer/scripts/build-mcp.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_DIR="$PLUGIN_ROOT/mcp/gemini-server"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}  Building Gemini MCP server${NC}"

if [[ ! -d "$MCP_DIR" ]]; then
  echo -e "${RED}  Error: MCP server source not found at $MCP_DIR${NC}"
  exit 1
fi

if [[ ! -f "$MCP_DIR/package.json" ]]; then
  echo -e "${RED}  Error: $MCP_DIR/package.json missing${NC}"
  exit 1
fi

cd "$MCP_DIR"

echo -e "${BLUE}    Installing MCP server dependencies...${NC}"
npm install --production=false 2>&1 | sed 's/^/    /'

echo -e "${BLUE}    Compiling MCP server...${NC}"
npm run build 2>&1 | sed 's/^/    /'

if [[ ! -f "$MCP_DIR/dist/index.js" ]]; then
  echo -e "${RED}  Error: build did not produce dist/index.js${NC}"
  exit 1
fi

echo -e "${GREEN}  Gemini MCP server built${NC}"
