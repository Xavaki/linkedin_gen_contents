import asyncio
from pathlib import Path
from textwrap import dedent

from agno.agent import Agent
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters
from agno.models.azure import AzureAIFoundry

import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT_AGNO = os.getenv("AZURE_OPENAI_ENDPOINT_AGNO")

model=AzureAIFoundry(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT_AGNO,
    id="gpt-4o-mini",
    api_version="2024-12-01-preview",
)


async def run_agent() -> None:
    async with MCPTools(command="python3 weather_mcp_server.py") as mcp_tools:
        agent = Agent(
            model=model,
            tools=[mcp_tools],
            instructions=dedent("""\
                You are a weather assistant. You can answer questions about the weather,
            """),
            markdown=True,
            show_tool_calls=True,
        )

        # Run the agent
        await agent.acli_app(stream=True)
        # await agent.aprint_response(message, stream=True)


# Example usage
if __name__ == "__main__":
    asyncio.run(run_agent())