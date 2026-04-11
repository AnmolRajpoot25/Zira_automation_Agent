"""
Subprocess entrypoint for the user-specific MCP server.
Reads credentials from env vars injected by the orchestrator.
Run as: python -m mcp_server.run_server
"""
import os
import asyncio
from mcp.server.stdio import stdio_server
from mcp_server.jira_mcp import create_jira_mcp_server


async def main():
    access_token = os.environ["ACCESS_TOKEN"]
    cloud_id = os.environ["CLOUD_ID"]
    account_id = os.environ["ACCOUNT_ID"]
    display_name = os.environ["DISPLAY_NAME"]

    server = create_jira_mcp_server(
        access_token=access_token,
        cloud_id=cloud_id,
        account_id=account_id,
        display_name=display_name,
    )

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
