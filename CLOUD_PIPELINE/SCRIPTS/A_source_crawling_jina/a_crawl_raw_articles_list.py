import requests
import json
import os
from datetime import datetime
from time import sleep
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def get_run_id():
    return os.getenv('RUNID')

def main(RUNID):
    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
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

    class Source(BaseModel):
        url: str
        source_name: str

    class SaveContent(BaseModel):
        url: str
        name: str
        raw_content: str
        crawl_time: str

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

    sources = get_sources()
    # print(sources)a

    def fetch_source_content(source: Source) -> str:
        source_url_jina = 'https://r.jina.ai/' + source.url
        source_url_raw_content = requests.get(source_url_jina).text
        return source_url_raw_content

    source_contents = []
    for source in sources:
        print(source.source_name)
        try:
            source_url_raw_content = fetch_source_content(source)
        except:
            print(f"Failed to fetch content for {source.source_name}. Skipping...")
            continue
        save_content_data = {
            'url': source.url,
            'name': source.source_name.lower().replace(' ', '_'),
            'raw_content': source_url_raw_content,
            'crawl_time': RUN_TIME
        }
        try:
            save_content = SaveContent(**save_content_data)
            source_contents.append(save_content)
        except ValidationError as e:
            print(f'Validation error for save_content: {save_content_data}')
            print(e)

    save_source_raw_contents(source_contents)

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)