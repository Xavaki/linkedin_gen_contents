from agno.agent import Agent
from agno.tools.newspaper import NewspaperTools
from agno.models.azure import AzureAIFoundry

import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT_AGNO = os.getenv("AZURE_OPENAI_ENDPOINT_AGNO")


if  __name__ == "__main__":
    model=AzureAIFoundry(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT_AGNO,
        id="gpt-4o-bmn",
        api_version="2024-12-01-preview",
    )

    agent = Agent(
        model=model, 
        tools=[NewspaperTools()],
        show_tool_calls=True,
        markdown=True,
        )

    agent.print_response("Please summarize https://en.wikipedia.org/wiki/Language_model")
