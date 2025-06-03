from openai import AzureOpenAI
from dotenv import load_dotenv
from datetime import datetime
import os
from azure.storage.blob import BlobServiceClient

load_dotenv('../.env')

TASK_NAME = "article_summarization_v0"

def get_run_id():
    return os.getenv('RUNID')

RUNID = get_run_id()
RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

input_container_name = output_container_name = error_container_name = 'azure-openai-batch-processing-files'

input_container = blob_service_client.get_container_client(input_container_name)
assert input_container.exists(), f"Input container '{input_container_name}' does not exist."

output_container = blob_service_client.get_container_client(output_container_name)
error_container = blob_service_client.get_container_client(error_container_name)

print(f"Run ID: {RUNID} at {RUN_TIME}")

AZURE_OPENAI_API_KEY=os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT=os.getenv('AZURE_OPENAI_ENDPOINT')
client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
)

def get_batchids():
    batchids = []
    for blob_info in input_container.list_blobs(name_starts_with=f"{RUNID}--{TASK_NAME}_BATCHID"):
        blob_name = blob_info.name
        id = blob_name.split('.')[0].split('_')[-1]
        batchid_blob = input_container.get_blob_client(blob_name)
        batchid = batchid_blob.download_blob().readall()
        batchids.append((batchid.decode('utf-8'), id))

    return batchids

batchids = get_batchids()
print(batchids)

def save_output_file(i, output):
    output_filename = f"{RUNID}--{TASK_NAME}_OUTPUT_{i}.jsonl"
    output_blob = output_container.get_blob_client(output_filename)
    output_blob.upload_blob(output, overwrite=True)
    print(f"Output saved to {output_filename}")

def save_error_file(i, error):
    error_filename = f"{RUNID}--{TASK_NAME}_ERROR_{i}.jsonl"
    error_blob = error_container.get_blob_client(error_filename)
    error_blob.upload_blob(error, overwrite=True)
    print(f"Error saved to {error_filename}")

for batch_id, i in batchids:
    batch_obj = client.batches.retrieve(batch_id)
    batch_status = batch_obj.status

    if batch_status != "completed":
        print(f"Batch {batch_id} is not completed. Status: {batch_status}")
        continue

    output_file_id = batch_obj.output_file_id
    if output_file_id:
        output = client.files.content(output_file_id).text.strip()
        if output:
            save_output_file(i, output)

    error_file_id = batch_obj.error_file_id
    if error_file_id:
        error_content = client.files.content(error_file_id).text.strip()
        if error_content:
            save_error_file(i, error_content)