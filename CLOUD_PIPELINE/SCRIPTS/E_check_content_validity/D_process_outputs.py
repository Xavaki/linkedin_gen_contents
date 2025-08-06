import json
import os
from dotenv import load_dotenv
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

TASK_NAME = "content_validation_v0"

def get_run_id():
    return os.getenv('RUNID')

def main(RUNID):

    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

    input_container_name = 'azure-openai-batch-processing-files'

    input_container = blob_service_client.get_container_client(input_container_name)
    assert input_container.exists(), f"Input container '{input_container_name}' does not exist."

    output_container_name = "relevant-articles-content"
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Output container '{output_container_name}' does not exist."

    print(f"Run ID: {RUNID} at {RUN_TIME}")

    for blob_info in input_container.list_blobs(name_starts_with=f"{RUNID}--{TASK_NAME}_OUTPUT"):
        blob_client = input_container.get_blob_client(blob_info.name)
        lines_raw = blob_client.download_blob().readall().decode('utf-8').splitlines()
        for line in lines_raw:
            output_dict = json.loads(line)
            model = output_dict.get("response").get("body").get("model")
            line_id = output_dict.get("custom_id")
            _, _, article_id = line_id.split("--")
            content_json = output_dict.get("response").get("body").get("choices")[0].get("message").get("content")
            content = json.loads(content_json)
            validity = content.get("validity")
            if validity == False:
                blob = output_container.get_blob_client(f"{RUNID}/{article_id}.json")
                if blob.exists():
                    print(f"Deleting blob: {blob.blob_name}")
                    blob.delete_blob()


if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)