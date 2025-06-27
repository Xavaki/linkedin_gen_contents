import json 
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import sys
from datetime import datetime

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def main(RUNID):
    RUN_TIME = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))
    output_container_name = 'raw-articles-list'
    output_container = blob_service_client.get_container_client(output_container_name)
    assert output_container.exists(), f"Output container '{output_container_name}' does not exist."


    def read_raw_articles_ddgs():
        input_container_name = 'raw-articles-list-ddgs'
        input_container = blob_service_client.get_container_client(input_container_name)
        input_blob_name = f"{RUNID}--{input_container_name.replace("-", "_")}.json"
        input_blob_client = input_container.get_blob_client(input_blob_name)
        raw_articles_ddgs = input_blob_client.download_blob().readall()
        raw_articles_ddgs = json.loads(raw_articles_ddgs)
        raw_articles_ddgs = [{**a, 'crawling_source' : 'ddgs'} for a in raw_articles_ddgs]
        print(f"Read {len(raw_articles_ddgs)} articles from DDGS container")
        return raw_articles_ddgs
    
    def read_raw_articles_jina():
        input_container_name = 'raw-articles-list-jina'
        input_container = blob_service_client.get_container_client(input_container_name)
        input_blob_name = f"{RUNID}--{input_container_name.replace("-", "_")}.json"
        input_blob_client = input_container.get_blob_client(input_blob_name)
        raw_articles_jina = input_blob_client.download_blob().readall()
        raw_articles_jina = json.loads(raw_articles_jina)
        raw_articles_jina = [{**a, 'crawling_source' : 'jina'} for a in raw_articles_jina]
        print(f"Read {len(raw_articles_jina)} articles from jina container")
        return raw_articles_jina
    
    def get_previously_crawled_articles():
        previously_crawled_articles = []
        for blob_info in output_container.list_blobs():
            blob_name = blob_info.name
            runid = blob_name.split("--")[0]
            # Skip if the blob is from the current run
            if runid == RUNID:
                continue
            data = blob_service_client.get_blob_client(output_container_name, blob_name).download_blob().readall().decode('utf-8')
            data = json.loads(data)
            for item in data:
                if 'article_title' in item:
                    previously_crawled_articles.append((item['article_title'], item['source_name']))
        return previously_crawled_articles
    
    raw_articles_ddgs = read_raw_articles_ddgs()
    raw_articles_jina = read_raw_articles_jina()
    all_crawled_raw_articles = raw_articles_ddgs + raw_articles_jina
    previously_crawled_articles = get_previously_crawled_articles()

    new_raw_articles = []
    for article in all_crawled_raw_articles:
        article_title = article.get('article_title')
        source_name = article.get('source_name')
        if (article_title, source_name) in previously_crawled_articles:
            print(f"Skipping previously crawled article: {article_title} from {source_name}")
            continue

        new_raw_articles.append(article)

    def save_new_raw_articles(new_articles):
        if not new_articles:
            print("No new articles to save.")
            return
        
        output_blob_name = f"{RUNID}--{output_container_name.replace('-', '_')}.json"
        output_blob_client = output_container.get_blob_client(output_blob_name)
        
        try:
            output_blob_client.upload_blob(json.dumps(new_articles), overwrite=True)
            print(f"Saved {len(new_articles)} new articles to {output_blob_name}")
        except Exception as e:
            print(f"Error saving new articles: {e}")
    
    save_new_raw_articles(new_raw_articles)


if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)