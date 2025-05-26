import os
import sys
import httpx
from pydantic import Field
from typing import Literal, Optional
from datetime import datetime, timezone
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import (
    EmptyResult,
    ErrorData,
    ToolAnnotations
)
API_KEY = os.getenv("LAMBDA_CAPTURE_API_KEY")
if not API_KEY:
    print("Warning: LAMBDA_CAPTURE_API_KEY not set in environment", file=sys.stderr)
    raise ValueError("LAMBDA_CAPTURE_API_KEY not set in environment")

mcp = FastMCP(
        name="Lambda Capture Economic Data",
        host="127.0.0.1", 
        port=8000,
        json_response=True
    )

@mcp.tool(description="Perform semantic search on Macroeconomic Data Knowledge Base from Federal Reserve, Bank of England, and European Central Bank.",
          annotations=ToolAnnotations(readOnlyHint=True,idempotentHint=True,openWorldHint=True,))
async def macroecon_semantic_search(
    query_text: str = Field(description="The search query text (e.g., Inflation expectations)"),
    score: float = Field(default=0.75, ge=0, le=1, description="Minimum relevance score threshold"),
    max_results: int = Field(default=10, ge=1, description="Maximum number of results to return"),
    type: list[Literal["text", "table", "chart"]] | None = Field(
        default=None, 
        description="Filter results by content type (text, table, or chart) or None for all"
    ),
    source: list[Literal["Federal Reserve", "Bank of England", "European Central Bank"]] | None = Field(
        default=None,
        description="Filter results by source institution or None for all"
    ),
    start_date: str = Field(
        default="2018-01-01",
        description="Start date for filtering results (YYYY-MM-DD). If request needs recent/latest data, set start_date nearest to today up to 3 months ago.",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: str = Field(
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        description="End date for filtering results (YYYY-MM-DD). if None, set to today - this is better for **most recent data**. default is today",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
) -> JSONResponse:

    # Request parameters
    params = {
        "api_key": API_KEY,
        "query_text": query_text,
        "max_results": max_results,
        "type": type,
        "source": source,
        "score": score,
        "start_date": start_date,
        "end_date": end_date
    }

    headers = {
        "Accept": "application/json"
    }

    # Make the request to Lambda Capture API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:    
            response = await client.request(
                "GET",
                "https://app.lambda-capture.com/semantic-search/",
                json=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            if not data or len(data) == 0:
                return EmptyResult() #[]
            else:
                total_tokens = sum(item.get("token_count", 0) for item in data)
                max_tokens = 2_000  # Claude's Pro context window size is 100_000
                if total_tokens > max_tokens:
                    # If we're over the limit, truncate the results
                    truncated_data = []
                    current_tokens = 0
                    for item in data:
                        item_tokens = item.get("token_count", 0)
                        if current_tokens + item_tokens > max_tokens:
                            break
                        truncated_data.append(item)
                        current_tokens += item_tokens
                    
                    # Add a warning about truncation
                    if truncated_data:
                        truncated_data[0]["warning"] = f"Results truncated due to token limit. Showing {len(truncated_data)} of {len(data)} results."
                    return truncated_data
                return data
        
        except httpx.HTTPError as e:
            if e.response is not None:
                raise McpError(
                    error=ErrorData(
                        code=e.response.status_code, message=e.response.json().get("error", "Unknown error")
                    )
                )
            else:
                raise McpError(
                    error=ErrorData(
                        code=500, message=str(e)
                    )
                )

if __name__ == "__main__":
    print("Lambda Capture MCP Server is running", file=sys.stderr)
    mcp.run()