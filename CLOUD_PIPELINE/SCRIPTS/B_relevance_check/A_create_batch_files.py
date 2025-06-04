import json
import re
import unicodedata
from math import ceil
from datetime import datetime
import os
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from azure.storage.blob import BlobServiceClient

import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

TASK_NAME = "relevance_check_v0"
DEPLOYMENT_NAME = "gpt-4o--batch-2"

def get_run_id():
    return os.getenv('RUNID')

def main(RUNID):

    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))
    input_container_name = "raw-articles-list"
    output_container_name = "azure-openai-batch-processing-files"
    input_container = blob_service_client.get_container_client(input_container_name)
    assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Output container '{output_container_name}' does not exist."
    input_blob = input_container.get_blob_client(f"{RUNID}--raw_articles_list.json")
    assert input_blob.exists(), f"Input blob '{RUNID}--source_raw_content.json' does not exist in container '{input_container_name}'."
    print(f"Run ID: {RUNID} at {RUN_TIME}")

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

    def get_raw_articles_list() -> list[RawArticle]:
        raw_articles_list = json.loads(input_blob.download_blob().readall().decode('utf-8'))
        return [RawArticle(**a) for a in raw_articles_list]

    raw_articles_list = get_raw_articles_list()
    n_to_process = len(raw_articles_list)
    print(f"Number of articles to process: {n_to_process}")

    prompts_per_batch_job = 200
    n_batch_jobs = ceil(n_to_process/prompts_per_batch_job)
    print("Creating {} batch files".format(n_batch_jobs))

    system_prompt = """
    You are a smart content curator for a LinkedIn thought leader. Given a news article, decide if it is highly relevant based on the following criteria:
        - It aligns with topics like: Artificial Intelligence, Leadership, Remote Work, Digital Transformation, Sustainability, Emerging Tech, Industry Trends, Organizational Culture, DEI, Future of Work, Cybersecurity, Productivity, Startups, Market Trends, or Personal Branding.
        - It provides useful insight, a new perspective, or credible data.
        - It is suitable for a professional audience.

    You must adhere to the provided criteria and schema.
    """

    def format_task_jsonl_line(task_id, deployment_name, user_input):
        jsonl_line_template = {
            "custom_id": task_id,
            "method": "POST",
            "url": "/chat/completions",
            "body": {
                "model": deployment_name,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt.replace("\n", "\\n")
                    },
                    {
                        "role": "user",
                        "content": user_input.replace("\n", "\\n")
                    }
                ],
                "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ArticleRelevanceCheck",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "relevance": {
                                "type": "integer",
                                "description": "Relevance score for the article, between 0 and 2, where 0 means not relevant, 1 means somewhat relevant, and 2 means highly relevant.",
                                "enum": [0, 1, 2]
                            },
                            "article_language": {
                                "type": "string",
                            }
                        },
                        "required": [
                            "relevance",
                            "article_language"
                        ],
                        "additionalProperties": False
                    }
                }
            }
            }
        }
        return jsonl_line_template

    def generate_jsonl_lines(chunk_id, chunk_items):
        for j,article_info in enumerate(chunk_items):
            article_id = article_info.article_id
            task_id = f"{RUNID}--{TASK_NAME}--{article_id}"
            deployment_name = DEPLOYMENT_NAME
            a = {
                "article_title" : article_info.article_title,
                "article_url" : article_info.article_url,
                "article_keywords" : article_info.article_keywords,
                "article_language" : article_info.article_language,
            }
            yield json.dumps(format_task_jsonl_line(task_id=task_id, deployment_name=deployment_name, user_input=json.dumps(a))) + "\n"

    for i in range(n_batch_jobs):
        print(i)
        chunk = raw_articles_list[i*prompts_per_batch_job:min(n_to_process, (i+1)*prompts_per_batch_job)]
        batchfilename = f"{RUNID}--{TASK_NAME}_BATCHFILE_{i}.jsonl"
        batchfile_blob  = output_container.get_blob_client(batchfilename)
        batchfile_blob.upload_blob(generate_jsonl_lines(chunk_id=i, chunk_items=chunk), overwrite=True, encoding='utf-8')
        print(f"Batch file {batchfilename} created with {len(chunk)} tasks.")

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)