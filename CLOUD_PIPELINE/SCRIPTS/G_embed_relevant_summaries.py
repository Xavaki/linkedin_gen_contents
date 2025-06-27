import tiktoken
import json
import pandas as pd
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def get_run_id():
    return os.getenv('RUNID')


def main(RUNID):

    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

    input_container_name = 'relevant-articles-summaries'
    output_container_name = 'relevant-articles-summaries-embeddings'

    input_container = blob_service_client.get_container_client(input_container_name)
    assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Output container '{output_container_name}' does not exist."

    input_blob = input_container.get_blob_client(f'{RUNID}--relevant_articles_summaries.json')
    assert input_blob.exists(), f"Input blob '{RUNID}--relevant_articles_summaries.json' does not exist."

    print(f"Run ID: {RUNID} at {RUN_TIME}")

    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    client = AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY
    )

    def get_summaries_to_embed():
        summaries = json.loads(input_blob.download_blob().readall())
        return summaries

    summaries = get_summaries_to_embed()
    n_summaries_to_embed = len(summaries)
    print(f"Number of summaries to embed: {n_summaries_to_embed}")

    encoding = tiktoken.encoding_for_model("text-embedding-3-small")

    chunked_summaries = [[]]
    running_token_count = 0

    for summary_obj in summaries:
        article_id = summary_obj['article_id']
        summary = summary_obj['summary']
        tokens = encoding.encode(summary)
        token_count = len(tokens)
        running_token_count += token_count
        if running_token_count > 8000:  # true limit is 8192, but we leave some space for safety
            chunked_summaries.append([])
            running_token_count = 0
        chunked_summaries[-1].append({"summary": summary, "article_id": article_id, "token_count": token_count})

    all_embeddings = []

    for i, chunk in enumerate(chunked_summaries):
        print(f"embedding chunk {i+1} of {len(chunked_summaries)} with {len(chunk)} summaries")
        chunk_article_ids = [s.get("article_id") for s in chunk]
        embedding_model = "text-embedding-3-small"
        response = client.embeddings.create(
            input=[s.get("summary") for s in chunk],
            model=embedding_model,
        )
        for article_id, item in zip(chunk_article_ids, response.data):
            all_embeddings.append({
                'article_id': article_id,
                'summary_embedding': item.embedding,
                'embedding_model': embedding_model,
            })

    pd_embeddings = pd.DataFrame(all_embeddings)
    pd_embeddings.head()

    def save_embeddings():
        output_blob_name = f"{RUNID}--relevant_articles_summaries_embeddings.json"
        output_blob_client = output_container.get_blob_client(output_blob_name)
        output_blob_client.upload_blob(json.dumps(all_embeddings, indent=4), overwrite=True)
        print(f"Relevant articles content saved to blob storage as {output_blob_name}")

    save_embeddings()

    return True

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)