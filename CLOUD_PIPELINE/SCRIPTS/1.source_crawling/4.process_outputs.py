# Import Required Libraries
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from time import sleep

from pydantic import BaseModel, ValidationError

from azure.storage.blob import BlobServiceClient

# Load environment variables
load_dotenv('../.env')

# Define constants
TASK_NAME = "source_parsing_v0"

def get_run_id():
    return os.getenv('RUNID')

RUNID = get_run_id()
RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

input_container_name = 'azure-openai-batch-processing-files'
output_container_name = 'raw-articles-list'

input_container = blob_service_client.get_container_client(input_container_name)
assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
output_container = blob_service_client.get_container_client(output_container_name)
assert output_container.exists(), f"Output container '{output_container_name}' does not exist."

print(f"Run ID: {RUNID} at {RUN_TIME}")

def read_outputs():
    outputs = []
    for blob_info in input_container.list_blobs(name_starts_with=f"{RUNID}--{TASK_NAME}_OUTPUT"):
        blob_client = input_container.get_blob_client(blob_info.name)
        lines_raw = blob_client.download_blob().readall().decode('utf-8').splitlines()
        for line in lines_raw:
            output_dict = json.loads(line)
            model = output_dict.get("response").get("body").get("model")
            line_id = output_dict.get("custom_id")
            content_json = output_dict.get("response").get("body").get("choices")[0].get("message").get("content")
            content = json.loads(content_json)
            outputs.append({
                "model": model,
                "line_id": line_id,
                "content": content
            })
    return outputs

def get_previously_crawled_article_titles():
    previously_crawled_article_titles = []
    for blob_info in output_container.list_blobs():
        blob_name = blob_info.name
        data = blob_service_client.get_blob_client(output_container_name, blob_name).download_blob().readall().decode('utf-8')
        data = json.loads(data)
        for item in data:
            if 'article_title' in item:
                previously_crawled_article_titles.append(item['article_title'])
    return previously_crawled_article_titles

class RawArticle(BaseModel):
    model: str
    run_id: str
    task_name: str
    source_name: str
    article_id: str
    article_title: str
    article_url: str
    article_keywords: list[str]
    article_language: str
    crawled_at: str

previously_crawled_article_titles = get_previously_crawled_article_titles()

new_raw_articles_list = []
for output in read_outputs():
    model = output['model']
    line_id = output['line_id']
    run_id, task_name, source_name = line_id.split("--")
    content = output['content']

    article_links_list = content.get("article_links_list", [])
    for article_link in article_links_list:
        article_title = article_link.get("title", "")
        article_url = article_link.get("url", "")
        article_keywords = article_link.get("keywords", [])
        article_language = article_link.get("language", "")
        article_id = source_name + "_" + datetime.now().strftime('%Y%m%d%H%M%S%f')

        sleep(0.01)

        if article_title in previously_crawled_article_titles:
            print(f"Skipping {article_title} as it has already been crawled.")
            continue

        try:
            raw_article = RawArticle(
                model=model,
                run_id=run_id,
                task_name=task_name,
                source_name=source_name,
                article_id=article_id,
                article_title=article_title,
                article_url=article_url,
                article_keywords=article_keywords,
                article_language=article_language,
                crawled_at=RUN_TIME
            )
            new_raw_articles_list.append(raw_article.model_dump())
        except ValidationError as e:
            print(f"Validation error for article '{article_title}'")
            continue

print(len(new_raw_articles_list))

def save_raw_articles_list():
    output_blob_name = f"{RUNID}--raw_articles_list.json"
    output_blob_client = output_container.get_blob_client(output_blob_name)
    output_blob_client.upload_blob(json.dumps(new_raw_articles_list, indent=4), overwrite=True)
    print(f"Raw articles list saved to blob storage as {output_blob_name}")

save_raw_articles_list()