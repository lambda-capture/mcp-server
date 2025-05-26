#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import axios from 'axios';

const API_KEY = process.env.LAMBDA_CAPTURE_API_KEY;
if (!API_KEY) {
  process.stderr.write("Error: LAMBDA_CAPTURE_API_KEY not set in environment\n");
  process.exit(1);
}
// Define schemas using Zod
const SemanticSearchSchema = z.object({
  query_text: z.string().describe("The search query text (e.g., \"Inflation expectations\"). **required parameter**."),
  score: z.number().min(0).max(1).optional().default(0.75).describe("Minimum relevance score threshold"),
  max_results: z.number().int().min(1).optional().default(10).describe("Maximum number of results to return"),
  type: z.array(z.enum(["text", "table", "chart"])).optional().describe("Filter results by content type (text, table, or chart) or None for all"),
  source: z.array(z.enum(["Federal Reserve", "Bank of England", "European Central Bank"])).optional().describe("Filter results by source institution or None for all"),
  start_date: z.string().optional().default("2018-01-01").describe("Start date for filtering results (YYYY-MM-DD). If request needs recent/latest data, set start_date nearest to today up to 3 months ago."),
  end_date: z.string().optional().describe("End date for filtering results (YYYY-MM-DD). if None, set to today - this is better for **most recent data**. default is today")
});

// Create MCP server instance
const server = new Server(
  {
    name: "lambda-capture-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Handle list tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "macroecon_semantic_search",
        description: "Perform semantic search on Macroeconomic Data Knowledge Base from Federal Reserve, Bank of England, and European Central Bank.",
        inputSchema: zodToJsonSchema(SemanticSearchSchema),
        annotations: {
          readOnlyHint: true,
          idempotentHint: true,
          openWorldHint: true 
        }
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    if (!request.params.arguments) {
      throw new Error("Arguments are required");
    }

    switch (request.params.name) {
      case "macroecon_semantic_search": {
        const args = SemanticSearchSchema.parse(request.params.arguments);
        const {
          query_text,
          max_results = 10,
          type,
          source,
          score = 0.75,
          start_date = "2018-01-01",
          end_date = new Date().toISOString().split('T')[0]
        } = args;

        try {
          const response = await axios.get('https://app.lambda-capture.com/semantic-search/', {
            data: {
              api_key: API_KEY,
              query_text,
              max_results,
              type,
              source,
              score,
              start_date,
              end_date
            },
            headers: {
              'Accept': 'application/json'
            }
          });

          const data = response.data;
          const maxTokens = 2_000; // Claude's Pro context window size is 100_000
          const totalTokens = data.reduce((sum: number, item: any) => sum + (item.token_count || 0), 0);

          if (totalTokens > maxTokens) {
            let truncatedData = [];
            let currentTokens = 0;

            for (const item of data) {
              const itemTokens = item.token_count || 0;
              if (currentTokens + itemTokens > maxTokens) break;
              truncatedData.push(item);
              currentTokens += itemTokens;
            }

            if (truncatedData.length > 0) {
              truncatedData[0].warning = `Results truncated due to token limit. Showing ${truncatedData.length} of ${data.length} results.`;
            }
            return {
              content: [{ type: "text", text: JSON.stringify(truncatedData, null, 2) }],
            };
          }

          return {
            content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
          };
        } catch (error) {
          if (axios.isAxiosError(error)) {
            const errorMessage = error.response?.data?.['error'] || error.message;
            throw new Error(`Lambda Capture semantic search failed: ${errorMessage}`);
          }
          throw error;
        }
      }

      default:
        throw new Error(`Unknown tool: ${request.params.name}`);
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(`Invalid input: ${JSON.stringify(error.errors)}`);
    }
    throw error;
  }
});

// Run the server
async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write("Lambda Capture MCP Server running on stdio\n");
}

runServer().catch((error) => {
  process.stderr.write(`Fatal Error: ${error}\n`);
  process.exit(1);
});