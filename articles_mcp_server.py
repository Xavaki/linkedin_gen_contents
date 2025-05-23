from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

from newspaper import Article

import os

import json


articles = []
for json_file in os.listdir("./local_tests_data/articles_list/"):
    if json_file.endswith(".json"):
        with open(f"./local_tests_data/articles_list/{json_file}", "r") as f:
            articles_list = json.load(f)
            articles += articles_list

# Initialize FastMCP server
mcp = FastMCP("articles")

# tools
@mcp.tool()
async def get_articles_list() -> str:
    """Get a list of articles.
    """
    return articles

@mcp.tool()
async def read_article_content(url : str) -> str:
    """Read the content of an article from a URL.

    Args:
        url: URL of the article
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(e)
        return f"Error reading article"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')