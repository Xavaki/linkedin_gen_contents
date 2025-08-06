import os
import json
from newspaper import Article
from time import sleep
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')


def main(RUNID):

    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))

    input_container_name = 'relevant-articles-list'
    output_container_name = 'relevant-articles-content'

    input_container = blob_service_client.get_container_client(input_container_name)
    assert input_container.exists(), f"Input container '{input_container_name}' does not exist."
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Output container '{output_container_name}' does not exist."

    input_blob = input_container.get_blob_client(f'{RUNID}--relevant_articles_list.json')
    assert input_blob.exists(), f"Input blob '{RUNID}--relevant_articles_list.json' does not exist."

    print(f"Run ID: {RUNID} at {RUN_TIME}")

    def read_relevant_articles_list():
        relevant_articles_list = json.loads(input_blob.download_blob().readall().decode('utf-8'))
        return relevant_articles_list

    relevant_articles_list = read_relevant_articles_list()
    # print(relevant_articles_list)

    for relevant_article in relevant_articles_list:
        url = relevant_article["article_url"]
        article_id = relevant_article["article_id"]
        title = relevant_article["article_title"]
        print(f"Processing {url}")
        sleep(1)  # Sleep to avoid overwhelming the server
        try:
            article = Article(url)
            article.download()
            article.parse()
        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue
        content = article.text
        publish_date = datetime.strftime(article.publish_date, "%Y-%m-%d") if article.publish_date else None
        if not content:
            print(f"Skipping {url} due to empty content")
            continue

        article_content_json = json.dumps({'article_id': article_id, 'content': content, 'title': title, 'publish_date': publish_date}, indent=4)
        output_container.get_blob_client(RUNID + "/" + article_id + ".json").upload_blob(article_content_json, overwrite=True)

    return True

if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)