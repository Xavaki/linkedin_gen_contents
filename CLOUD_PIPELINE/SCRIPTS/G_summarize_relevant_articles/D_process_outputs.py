import json
import os
from dotenv import load_dotenv
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

TASK_NAME = "article_summarization_v0"

def get_run_id():
    return os.getenv('RUNID')

def main(RUNID):

    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

    input_container_name = 'azure-openai-batch-processing-files'
    output_container_name = 'relevant-articles-summaries'

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
                _, _, article_id = line_id.split("--")
                summary = output_dict.get("response").get("body").get("choices")[0].get("message").get("content")
                outputs.append({
                    "model": model,
                    "summary": summary,
                    "article_id": article_id,
                    "run_id": RUNID,
                    "task_name": TASK_NAME,
                })
        return outputs

    outputs = read_outputs()
    # print(outputs)

    def save_outputs():
        output_blob_name = f"{RUNID}--relevant_articles_summaries.json"
        output_blob_client = output_container.get_blob_client(output_blob_name)
        output_blob_client.upload_blob(json.dumps(outputs, indent=4), overwrite=True)
        print(f"Relevant articles list saved to blob storage as {output_blob_name}")

    save_outputs()

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)