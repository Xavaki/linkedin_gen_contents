import sys
import os
from pathlib import Path

from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.orchestrator import main as source_crawling
from CLOUD_PIPELINE.SCRIPTS.B_relevance_check.orchestrator import main as relevance_check
from CLOUD_PIPELINE.SCRIPTS.C_read_relevant_articles import main as read_relevant_articles
from CLOUD_PIPELINE.SCRIPTS.D_summarize_relevant_articles.orchestrator import main as summarize_relevant_articles
from CLOUD_PIPELINE.SCRIPTS.E_embed_relevant_summaries import main as embed_relevant_summaries

from dotenv import load_dotenv

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def main(RUNID: str):
    print("Starting pipeline with RUNID: {}".format(RUNID))
    
    source_crawling_success = source_crawling(RUNID)
    if not source_crawling_success:
        print("Source crawling failed. Exiting pipeline.")
        return

    relevance_check_success = relevance_check(RUNID)
    if not relevance_check_success:
        print("Relevance check failed. Exiting pipeline.")
        return

    read_relevant_articles_success = read_relevant_articles(RUNID)
    if not read_relevant_articles_success:
        print("Reading relevant articles failed. Exiting pipeline.")
        return
    
    summarize_relevant_articles_success = summarize_relevant_articles(RUNID)
    if not summarize_relevant_articles_success:
        print("Summarizing relevant articles failed. Exiting pipeline.")
        return
    
    embed_relevant_summaries_success = embed_relevant_summaries(RUNID)
    if not embed_relevant_summaries_success:
        print("Embedding relevant summaries failed. Exiting pipeline.")
        return

if __name__ == "__main__":
    RUNID = sys.argv[1]
    run_accepted = input("About to run the pipeline with RUNID: {}. Do you accept? (y/n): ".format(RUNID))
    run_accepted = run_accepted == 'y'
    if run_accepted:
        main(RUNID)
    else:
        print("Pipeline run cancelled.")
