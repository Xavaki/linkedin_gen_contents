import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from datetime import datetime
from azure.storage.blob import BlobServiceClient

load_dotenv('../.env')

TASK_NAME = "source_parsing_v0"

def get_run_id():
    return os.getenv('RUNID')

RUNID = get_run_id()
RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))
input_container_name = output_container_name = 'azure-openai-batch-processing-files'
input_container = blob_service_client.get_container_client(input_container_name)
assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
output_container = blob_service_client.get_container_client(output_container_name)
print(f"Run ID: {RUNID} at {RUN_TIME}")

AZURE_OPENAI_API_KEY=os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT=os.getenv('AZURE_OPENAI_ENDPOINT')
client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
)

def get_batchfiles():
    batchfiles = []
    for blob_info in input_container.list_blobs(name_starts_with=f"{RUNID}--{TASK_NAME}_BATCHFILE"):
        name = blob_info.name
        b = {
            'path': name,
            'id' : name.split('.')[0].split('_')[-1],
        }
        batchfiles.append(b)
    return sorted(batchfiles)

batchfiles = get_batchfiles()

def save_batchid(i, batch_id):
    batchid_filename = f"{RUNID}--{TASK_NAME}_BATCHID_{i}.txt"
    batchid_blob = output_container.get_blob_client(batchid_filename)
    batchid_blob.upload_blob(batch_id, overwrite=True)
    print(f"Saved batch ID {batch_id} to {batchid_filename}")

for bathcfile in batchfiles:
    i = bathcfile['id']
    path = bathcfile['path']
    print(f"Submitting {path}")
    batchfile_blob = input_container.get_blob_client(path)
    temp_local_name = path
    with open(temp_local_name, "wb") as file:
        file.write(batchfile_blob.download_blob().readall())
    file = client.files.create(
        file=open(path, "rb"),
        purpose="batch"
    )
    os.remove(temp_local_name)
    print(file.model_dump_json(indent=2))
    file_id = file.id
    batch_response = client.batches.create(
        input_file_id=file_id,
        endpoint="/chat/completions",
        completion_window="24h",
    )
    batch_id = batch_response.id
    print(batch_response.model_dump_json(indent=2))
    save_batchid(i, batch_id)
    print("Batch job submitted successfully.")
    print("  ")