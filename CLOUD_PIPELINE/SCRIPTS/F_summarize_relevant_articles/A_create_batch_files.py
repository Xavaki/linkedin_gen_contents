import json
from math import ceil
from datetime import datetime
import os

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

import sys


load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

TASK_NAME = "article_summarization_v0"
DEPLOYMENT_NAME = "gpt-4o--batch-2"


def main(RUNID):

    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

    input_container_name = 'relevant-articles-content'
    output_container_name = 'azure-openai-batch-processing-files'

    input_container = blob_service_client.get_container_client(input_container_name)
    assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Output container '{output_container_name}' does not exist."

    print(f"Run ID: {RUNID} at {RUN_TIME}")

    def get_relevant_articles_content_blob_names():
        relevant_articles_content_blob_names = input_container.list_blobs(name_starts_with=f"{RUNID}")
        return relevant_articles_content_blob_names

    relevant_articles_content_blob_names = get_relevant_articles_content_blob_names()
    n_to_process = len(relevant_articles_content_blob_names)
    print(f"Number of articles to process: {n_to_process}")
    # print(relevant_articles_content[0])

    prompts_per_batch_job = 200
    n_batch_jobs = ceil(n_to_process/prompts_per_batch_job)
    print("Creating {} batch files".format(n_batch_jobs))

    system_prompt = """
    You are a professional content assistant summarizing articles for a LinkedIn thought leader. Your task is to summarize the article in 3 to 8 sentences.

    Focus on:
    - The main idea or thesis
    - The most important insight or data
    - Why it matters to professionals or business leaders

    Use clear, concise, and neutral professional English. Avoid fluff, opinion, or casual tone.

    **Important:** The summary must be written in English ONLY — even if the source article is written in another language. Do not translate the article; just summarize its core ideas in English.
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
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_input
                    }
                ]
            }
        }
        return jsonl_line_template

    def generate_jsonl_lines(chunk_id, chunk_items):
        for j,relevant_article in enumerate(chunk_items):
            article_id = relevant_article["article_id"]
            article_content = relevant_article["content"]
            task_id = f"{RUNID}--{TASK_NAME}--{article_id}"
            deployment_name = DEPLOYMENT_NAME
            yield json.dumps(format_task_jsonl_line(task_id=task_id, deployment_name=deployment_name, user_input=article_content)) + "\n"

    for i in range(n_batch_jobs):
        print(i)
        chunk_names = relevant_articles_content_blob_names[i*prompts_per_batch_job:min(n_to_process, (i+1)*prompts_per_batch_job)]
        chunk = [json.loads(input_container.get_blob_client(blob.name).download_blob().readall().decode('utf-8')) for blob in chunk_names]
        batchfilename = f"{RUNID}--{TASK_NAME}_BATCHFILE_{i}.jsonl"

        batchfile_blob  = output_container.get_blob_client(batchfilename)
        batchfile_blob.upload_blob(generate_jsonl_lines(chunk_id=i, chunk_items=chunk), overwrite=True, encoding='utf-8')
        print(f"Batch file {batchfilename} created with {len(chunk)} tasks.")

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)