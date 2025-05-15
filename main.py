from mcp.server.fastmcp import FastMCP
import os
import sys
import httpx
from typing import Literal, Optional
from datetime import datetime, timezone

API_KEY = os.getenv("LAMBDA_CAPTURE_API_KEY")
if not API_KEY:
    print("Warning: LAMBDA_CAPTURE_API_KEY not set in environment", file=sys.stderr)
    raise ValueError("LAMBDA_CAPTURE_API_KEY not set in environment")

mcp = FastMCP(
        name="Lambda Capture Economic Data",
        host="127.0.0.1", 
        port=8000,
    )

@mcp.tool(description="Perform semantic search on Macroeconomic Data Knowledge Base from Federal Reserve, Bank of England, and European Central Bank.")
async def macroecon_semantic_search(
    query_text: str,
    max_results: int = 10,
    type: list[Literal["text", "table", "chart"]] | None = None,
    source: list[Literal["Federal Reserve", "Bank of England", "European Central Bank"]] | None = None,
    score: float = 0.75,
    start_date: str = "2018-01-01",
    end_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
) -> list[dict]:
    """
    Perform semantic search on Macroeconomic Data Knowledge Base from Federal Reserve, Bank of England, and European Central Bank.
    
    Args:
        api_key: Your Lambda Capture API key. **required parameter**.
        query_text: The search query text (e.g., "Inflation expectations"). **required parameter**.
        max_results: Maximum number of results to return (default: 10)
        type: List of content types to filter by (e.g., ["text", "table", "chart"] or None for all)
        source: List of sources to filter by (e.g., ["Federal Reserve", "Bank of England", "European Central Bank"] or None for all)
        score: Minimum similarity score (0-1, default: 0.75)
        start_date: Start date for filtering results (YYYY-MM-DD). Default is 2018-01-01. If request needs recent/latest data, set nearest date to today up to 3 months ago.
        end_date: End date for filtering results (YYYY-MM-DD). Default is today's date.
    
    Returns:
        List of relevant search results from Macroeconomic Data Knowledge Base.
    """

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
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                "GET",
                "https://app.lambda-capture.com/semantic-search/",
                json=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            # Check for context window overflow
            total_tokens = sum(item.get("token_count", 0) for item in data)
            max_tokens = 100_000  # Claude's context window size
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
                error_msg = e.response.json().get("error message", str(e))
            else:
                error_msg = str(e)
            raise Exception(f"Lambda Capture semantic search failed: {error_msg}", file=sys.stderr)

if __name__ == "__main__":
    print("Lambda Capture MCP Server is running", file=sys.stderr)
    mcp.run()