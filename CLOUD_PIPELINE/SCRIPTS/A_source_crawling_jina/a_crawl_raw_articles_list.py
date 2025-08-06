import requests
import json
import os
from datetime import datetime
from time import sleep
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import sys

import asyncio
import aiohttp

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')
RUN_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class Source(BaseModel):
    url: str
    source_name: str

class SaveContent(BaseModel):
    url: str
    name: str
    raw_content: str
    crawl_time: str

async def fetch_source_content(session, url) -> str:
    try:
        async with session.get(url) as response:
            if response.status == 429: # rate limit exceeded
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after else 5
                print(f"Rate limited. Retrying {url} after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                return await fetch_source_content(session, url)  # retry

            if response.status != 200:
                raise Exception(f"Failed to fetch {url}: {response.status}")
            
            response_text = await response.text()
            return response_text

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def get_source_content(session, source: Source) -> str:
    print(f"Fetching content from {source.source_name}...")
    source_url_jina = 'https://r.jina.ai/' + source.url
    fetched_content = await fetch_source_content(session, source_url_jina)
    if fetched_content is None:
        print(f"Failed to fetch content for {source.source_name}.")
        return None
    
    save_content_data = {
        'url': source.url,
        'name': source.source_name.lower().replace(' ', '_'),
        'raw_content': fetched_content,
        'crawl_time': RUN_TIME
    }
    try:
        save_content = SaveContent(**save_content_data)
        print(f"Successfully fetched content from {source.source_name}.")
        return save_content
    except ValidationError as e:
        print(f'Content validation error for source: {source.source_name}')
        print(e)
        return None
    
semaphore = asyncio.Semaphore(3)  # limit to 3 concurrent requests
async def get_source_content_semaphore(session, source):
    async with semaphore:
        return await get_source_content(session, source)
    
async def get_all_sources(sources: list[Source]) -> list[SaveContent]:
    async with aiohttp.ClientSession() as session:
        tasks = [get_source_content_semaphore(session, source) for source in sources]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result is not None]

def main(RUNID):
    print(f"Run ID: {RUNID} at {RUN_TIME}")

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))
    input_container_name = 'sources'
    output_container_name = 'source-raw-content'
    input_container = blob_service_client.get_container_client(input_container_name)
    assert input_container.exists(), f"Container '{input_container_name}' does not exist."
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Container '{output_container_name}' does not exist."
    input_blob = input_container.get_blob_client("sources.json")
    assert input_blob.exists(), f"Blob 'sources_{RUNID}.json' does not exist in container '{input_container_name}'."
    output_blob = output_container.get_blob_client(f"{RUNID}--source_raw_content.json")

    def get_sources() -> list[Source]:
        sources = json.loads(input_blob.download_blob().readall().decode('utf-8'))
        validated_sources = []
        for source in sources:
            try:
                validated_source = Source(**source)
                validated_sources.append(validated_source)
            except ValidationError as e:
                print(f'Validation error for source: {source}')
                print(e)
        return validated_sources

    def save_source_raw_contents(save_contents: SaveContent) -> None:
        output_blob.upload_blob(
            json.dumps([x.model_dump() for x in save_contents], indent=4).encode('utf-8'),
            overwrite=True
        )
        print(f"Saved raw contents to {output_blob.blob_name}")

    sources = get_sources()
    source_contents = asyncio.run(get_all_sources(sources))
    save_source_raw_contents(source_contents)

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)