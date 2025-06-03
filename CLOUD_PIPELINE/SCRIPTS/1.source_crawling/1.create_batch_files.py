import json
from math import ceil
from datetime import datetime
import os
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv('../.env')

TASK_NAME = "source_parsing_v0"
DEPLOYMENT_NAME = "gpt-4o--batch-2"

def get_run_id():
    return os.getenv('RUNID')

RUNID = get_run_id()
RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))
input_container_name = 'source-raw-content'
output_container_name = 'azure-openai-batch-processing-files'
input_container = blob_service_client.get_container_client(input_container_name)
assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
output_container = blob_service_client.get_container_client(output_container_name)
assert output_container.exists(), f"Output container '{output_container_name}' does not exist."
input_blob = input_container.get_blob_client(f"{RUNID}--source_raw_content.json")
assert input_blob.exists(), f"Input blob '{RUNID}--source_raw_content.json' does not exist in container '{input_container_name}'."
print(f"Run ID: {RUNID} at {RUN_TIME}")

class RawContent(BaseModel):
    url: str
    name: str
    raw_content: str
    crawl_time: str

def get_source_raw_contents() -> list[RawContent]:
    source_raw_contents = []
    for src in json.loads(input_blob.download_blob().readall().decode('utf-8')):
        try:
            validated_data = RawContent(**src)
            source_raw_contents.append(validated_data)
        except ValidationError as e:
            print(f"Validation error for file {src.get('name')}: {e}")
            continue
    return source_raw_contents

source_raw_contents = get_source_raw_contents()
# print(source_raw_contents)

prompts_per_batch_job = 200
n_to_process = len(source_raw_contents)
n_batch_jobs = ceil(n_to_process/prompts_per_batch_job)
print("Creating {} batch files".format(n_batch_jobs))

system_prompt = """
Extract an article list from the following page content. Do not make up any information that's not in the provided text. If the provided content text contains no articles list (for instance due to a 'page not found' error), return an empty list.

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
                "name": "ArticleLinksList",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "article_links_list": {
                            "type": "array",
                            "items" : {"$ref": "#/$defs/article_link"}
                        },
                    },
                    "$defs": {
                        "article_link" : {
                            "type" : "object",
                            "properties" : {
                                "title" : {
                                    "type": "string"
                                },
                                "url" : {
                                    "type": "string",
                                },
                                "keywords" : {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "language": {
                                    "type": "string",
                                },
                            },
                            "required": [
                                "title",
                                "url",
                                "keywords",
                                "language"
                            ],
                            "additionalProperties": False
                        }
                    },
                    "required": [
                        "article_links_list",
                    ],
                    "additionalProperties": False
                }
            }
        }
        }
    }
    return jsonl_line_template

def generate_jsonl_lines(chunk_id, chunk_items):
    for j,source_info in enumerate(chunk_items):
        source_name = source_info.name 
        raw_content = source_info.raw_content 
        task_id = f"{RUNID}--{TASK_NAME}--{source_name}"
        deployment_name = DEPLOYMENT_NAME
        yield json.dumps(format_task_jsonl_line(task_id=task_id, deployment_name=deployment_name, user_input=raw_content)) + "\n"

for i in range(n_batch_jobs):
    print(i)
    chunk = source_raw_contents[i*prompts_per_batch_job:min(n_to_process, (i+1)*prompts_per_batch_job)]
    batchfilename = f"{RUNID}--{TASK_NAME}_BATCHFILE_{i}.jsonl"
    batchfile_blob  = output_container.get_blob_client(batchfilename)
    batchfile_blob.upload_blob(generate_jsonl_lines(chunk_id=i, chunk_items=chunk), overwrite=True, encoding='utf-8')
    print(f"Batch file {batchfilename} created with {len(chunk)} tasks.")