# Lambda Capture MCP Server
MCP implementation of our standard [Semantic Search API for Macroeconomic Data](https://github.com/lambda-capture/Semantic-Search-API)
![Lambda Capture MCP Server](logo.png)
## Pre-requisites
- [Lambda Capture API key](https://lambda-capture.com/)
- for MCP Typescript: [Node.js 18+ (includes npx and npm)](https://nodejs.org/en/download/)
- for MCP Python: [Python 3.11+](https://www.python.org/downloads/)


## Installation
1. Clone the repo  
### Node:
2. `npm install` to install the dependencies
3. `npm run build` to build the project  
### Python:
2. `python -m venv .venv` create virtual environment
3. `source .venv/bin/activate` activate virtual environment
4. `pip install -r requirements.txt` install the dependencies

## Configure your MCP Client (Claude Desktop)
Go to Claude -> Settings -> Developer -> Edit Config. Add the following to your `claude_desktop_config.json`  
### Node: 
```json
{
  "mcpServers": {
    "lambda-capture": {
      "command": "node",
      "args": [
        "/Absolute Path to/mcp-server/dist/index.js"
      ],
      "env": {
        "LAMBDA_CAPTURE_API_KEY": "Your API Key string"
      },
      "description": "Runs the Python MCP with Lambda Capture Macroeconomic Data API"
    }
  }
}
```  
### Python: 
```json
{
  "mcpServers": {
    "lambda-capture-mcp": {
      "command": "/Absolute Path to/.venv/bin/python",
      "args": [
        "/Absolute Path to/mcp-server/main.py"
      ],
      "env": {
        "LAMBDA_CAPTURE_API_KEY": "Your API Key string"
      },
      "description": "Runs the Python MCP with Lambda Capture Macroeconomic Data API"
    }
  }
}
```
© 2025 Lambda Capture Limited (Registration Number 15845351) 52 Tabernacle Street, London, EC2A 4NJ - All rights reserved