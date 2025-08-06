import json
from math import ceil
from datetime import datetime
import os
from dotenv import load_dotenv
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

    def get_raw_articles_list():
        raw_articles_list = json.loads(input_blob.download_blob().readall().decode('utf-8'))
        for article in raw_articles_list:
            crawling_source = article['crawling_source']
            if crawling_source == 'jina':
                article['article_info'] = "keywords: " + ", ".join(article['article_keywords']) + "\n"
            elif crawling_source == 'ddgs':
                article['article_info'] = article['article_body']
        return raw_articles_list

    raw_articles_list = get_raw_articles_list()
    n_to_process = len(raw_articles_list)
    print(f"Number of articles to process: {n_to_process}")

    prompts_per_batch_job = 200
    n_batch_jobs = ceil(n_to_process/prompts_per_batch_job)
    print("Creating {} batch files".format(n_batch_jobs))

    system_prompt = """
You are an assistant trained to evaluate the relevance of news articles for a group of high-level executives at the Spanish brewery Damm. Based on each executive’s professional focus and the geographic scope of the article, assess how relevant the article would be for them to engage with (e.g., via a professional LinkedIn post).

Use this scoring scale:
- 0 = Not relevant — The topic has no clear connection to the executive’s role or is out of geographic scope (e.g., regional/local content from unrelated markets).
- 1 = Somewhat relevant — The article touches loosely on their domain or has partial relevance, but may lack strong strategic value.
- 2 = Highly relevant — The article directly supports or relates to the executive’s role, values, or public communication focus, and is national (Spain) or global in scope.

**Important**: Articles that are primarily local/regional (e.g., about a single city or local initiative outside Spain without broader impact) should be scored **0**, even if thematically aligned.

Use this executive reference:

- **LAURA GIL** (Chief Digital & Data Officer): Focused on data strategy, AI, digital transformation, and innovation. Interested in tech adoption in traditional industries.
- **FEDE SEGARRA** (Chief Communications Officer): Focused on brand communication, reputation, storytelling, and public image.
- **ELÍSABETH HERNÁNDEZ** (HR Development Director): Focused on talent development, CSR, internal communication, and cross-functional collaboration.
- **JAUME ALEMANY** (Chief Marketing Officer): Focused on marketing innovation, branding, consumer trends, and maintaining brand heritage.
- **RICARDO LECHUGA** (HR Director): Focused on organizational culture, employee engagement, leadership proximity, and digital HR transformation.
- **JORGE VILLAVECCHIA** (President): Focused on corporate strategy, sustainability, growth, innovation, and long-term vision.
- **SALVADOR MARTÍNEZ** (Chief Financial Officer): Focused on financial strategy, sustainable finance, decision-making support, and ethical value creation.
- **JOFRE RIERA** (Sponsorships Manager): Focused on sports and cultural sponsorships, community engagement, and value-based partnerships.

Return your result as a JSON object of the form:
{"LAURA GIL": 2, "FEDE SEGARRA": 0, ...}

Here is the article to evaluate:
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
                                "LAURA GIL": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive LAURA GIL",
                                    "enum": [0, 1, 2]
                                },
                                "FEDE SEGARRA": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive FEDE SEGARRA",
                                    "enum": [0, 1, 2]
                                },
                                "ELÍSABETH HERNÁNDEZ": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive ELÍSABETH HERNÁNDEZ",
                                    "enum": [0, 1, 2]
                                },
                                "JAUME ALEMANY": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive JAUME ALEMANY",
                                    "enum": [0, 1, 2]
                                },
                                "RICARDO LECHUGA": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive RICARDO LECHUGA",
                                    "enum": [0, 1, 2]
                                },
                                "JORGE VILLAVECCHIA": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive JORGE VILLAVECCHIA",
                                    "enum": [0, 1, 2]
                                },
                                "SALVADOR MARTÍNEZ": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive SALVADOR MARTÍNEZ",
                                    "enum": [0, 1, 2]
                                },
                                "JOFRE RIERA": {
                                    "type": "integer",
                                    "description": "Article relevance score for executive JOFRE RIERA",     
                                    "enum": [0, 1, 2]
                                },
                                "article_language": {
                                    "type": "string",
                                    "enum": ["es", "ca", "en"],
                                } 
                            },
                            "required": [
                                "LAURA GIL",
                                "FEDE SEGARRA",
                                "ELÍSABETH HERNÁNDEZ",
                                "JAUME ALEMANY",
                                "RICARDO LECHUGA",
                                "JORGE VILLAVECCHIA",
                                "SALVADOR MARTÍNEZ",
                                "JOFRE RIERA",  
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
            article_id = article_info["article_id"]
            task_id = f"{RUNID}--{TASK_NAME}--{article_id}"
            deployment_name = DEPLOYMENT_NAME
            yield json.dumps(format_task_jsonl_line(task_id=task_id, deployment_name=deployment_name, user_input=json.dumps(article_info))) + "\n"

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