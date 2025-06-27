from duckduckgo_search import DDGS
from time import sleep
import pandas as pd
from pydantic import BaseModel, ValidationError
from time import time
import json 
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import sys

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def main(RUNID):
    def search_news_by_keywords(keyword, persona_name, max_results=10000):
        search_term = keyword 
        with DDGS() as ddgs:
            results = ddgs.news(
                keywords=search_term,
                region="es-es",
                safesearch="Moderate",
                timelimit="w",
                max_results=max_results
            )
            return [{"persona": persona_name, "query": search_term, **r} for r in results]
        
    persona_keywords = {
        "Laura Gil": [
            "inteligencia artificial", 
            # "datos", 
            "transformación digital",
            "cultura de innovación"
        ],
        "Fede Segarra": [
            "comunicación corporativa", 
            "estrategias de comunicación", 
            "imagen pública"
        ],
        "Elísabeth Hernández": [
            "recursos humanos", 
            "formación corporativa", 
            "voluntariado"
        ],
        "Jaume Alemany": [
            "marketing", 
            "branding", 
            "campañas publicitarias"
        ],
        "Ricardo Lechuga": [
            "transformación cultural", 
            "desarrollo del talento", 
            "digitalización RRHH", 
        ],
        "Jorge Villavecchia": [
            "liderazgo empresarial", 
            "estrategia corporativa", 
            "sostenibilidad", 
            # "transformación de negocios", 
            # "expansión internacional"
        ],
        "Salvador Martínez": [
            # "finanzas sostenibles", 
            "crecimiento responsable", 
            "decisiones basadas en datos", 
            "ética empresarial"
        ],
        "Jofre Riera": [
            "patrocinios deportivos", 
            "marketing cultural", 
            "experiencias de marca", 
            # "impacto social"
        ]
    }

    all_results = []
    for persona, keywords in persona_keywords.items():
        keyword_results = []
        for keyword in keywords:
            results = search_news_by_keywords(keyword, persona)
            keyword_results.extend(results)
            print(f"Results for {persona} on '{keyword}': {len(results)} found.")
            print(f"Sleeping for 20 seconds to avoid rate limiting...")
            sleep(20)
            
        all_results.extend(keyword_results)


    class RawArticle(BaseModel):
        run_id: str
        source_name: str
        source_url: str
        article_id: str
        article_date: str
        article_title: str
        article_url: str
        article_body: str
        article_image_url: str
        article_language: str
        crawled_at: str
        ddgs_search_query: list[str]
        query_original_personas: list[str]


    df_results = pd.DataFrame(all_results)
    # drop rows with missing url
    df_results.dropna(subset=['url'], inplace=True)

    agg_clause = {col : 'first' for col in df_results.columns}
    agg_clause.pop('url')
    agg_clause['persona'] = lambda x: list(x)
    agg_clause['query'] = lambda x: list(x)
    df_results = df_results.groupby('url').agg(agg_clause).reset_index()

    df_results["source_url"] = df_results["url"].apply(lambda x: "/".join(x.split("/")[:3]) if pd.notna(x) else None)
    df_results["source"] = df_results["source"].apply(lambda x: x.replace(" ", "_").lower() if pd.notna(x) else None)
    df_results["article_id"] = df_results["source"].apply(lambda x: x + "_" + str(time()).replace(".", "") if pd.notna(x) else None)
    df_results.dropna(subset=["source_url", "source", "article_id"], inplace=True)
    df_results["crawled_at"] = pd.to_datetime("now").isoformat()
    df_results["article_language"] = "es"  
    df_results["run_id"] = RUNID

    df_results.rename(columns={
        "title": "article_title",
        "url": "article_url",
        "body": "article_body",
        "image": "article_image_url",
        "source": "source_name",
        "query": "ddgs_search_query",
        "persona": "query_original_personas",
        "date" : "article_date"
    }, inplace=True)


    # convert to RawArticle model
    raw_articles = []
    for _, row in df_results.iterrows():
        try:
            article = RawArticle(
                run_id=row["run_id"],
                source_name=row["source_name"],
                source_url=row["source_url"],
                article_id=row["article_id"],
                article_date=row["article_date"],
                article_title=row["article_title"],
                article_url=row["article_url"],
                article_body=row["article_body"],
                article_image_url=row["article_image_url"],
                article_language=row["article_language"],
                crawled_at=row["crawled_at"],
                ddgs_search_query=row["ddgs_search_query"],
                query_original_personas=row["query_original_personas"]
            )
            raw_articles.append(article.model_dump())
        except ValidationError as e:
            print(f"Validation error for row {row['article_id']}: {e}")

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING'))
    output_container_name = 'raw-articles-list-ddgs'
    output_container = blob_service_client.get_container_client(output_container_name)
    output_blob_name = f"{RUNID}--{output_container_name.replace("-", "_")}.json"
    output_blob_client = output_container.get_blob_client(output_blob_name)
    output_blob_client.upload_blob(json.dumps(raw_articles, indent=4), overwrite=True)
    print(f"Relevant articles list saved to blob storage as {output_blob_name}")


if __name__ == "__main__":
    RUNID = sys.argv[1]
    main(RUNID)