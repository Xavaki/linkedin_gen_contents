import sys
import os

from azure.storage.blob import BlobServiceClient
import json

from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.orchestrator import main as source_crawling
from CLOUD_PIPELINE.SCRIPTS.B_relevance_check.orchestrator import main as relevance_check
from CLOUD_PIPELINE.SCRIPTS.C_read_relevant_articles import main as read_relevant_articles
from CLOUD_PIPELINE.SCRIPTS.D_summarize_relevant_articles.orchestrator import main as summarize_relevant_articles
from CLOUD_PIPELINE.SCRIPTS.E_embed_relevant_summaries import main as embed_relevant_summaries

from dotenv import load_dotenv

load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def main(RUNID: str):
    print("Starting pipeline with RUNID: {}".format(RUNID))
    
    try:
        source_crawling(RUNID)
    except Exception as e:
        return False, "source_crawling", e

    try:
        relevance_check(RUNID)
    except Exception as e:
        return False, "relevance_check", e

    try:
        read_relevant_articles(RUNID)
    except Exception as e:
        return False, "read_relevant_articles", e
    
    try:
        summarize_relevant_articles(RUNID)
    except Exception as e:
        return False, "summarize_relevant_articles", e

    try:    
        embed_relevant_summaries(RUNID)
    except Exception as e:
        return False, "embed_relevant_summaries", e
    
    return True, None, None

if __name__ == "__main__":

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING"))
    runs_metadata_blob = blob_service_client.get_blob_client(container="runs-metadata", blob="runs_metadata.json")
    runs_metadata = json.loads(runs_metadata_blob.download_blob().readall())

    run_ids = sorted([r.get("RUNID") for r in runs_metadata])
    next_run_id = f"RUNID_{int(run_ids[-1].split("_")[-1]) + 1}"

    print("RUNID", next_run_id)

    pipeline_success, failed_step, error = main(next_run_id)

    if pipeline_success:
        print("Pipeline completed successfully for RUNID: {}".format(next_run_id))
        runs_metadata.append({
            "RUNID": next_run_id,
            "status": "success",
        })
        runs_metadata_blob.upload_blob(json.dumps(runs_metadata), overwrite=True)
    else:
        print("Pipeline failed at step: {} with error: {}".format(failed_step, error))
        runs_metadata.append({
            "RUNID": next_run_id,
            "status": "failed",
            "failed_step": failed_step,
            "error": str(error)
        })
        runs_metadata_blob.upload_blob(json.dumps(runs_metadata), overwrite=True)

    # RUNID = sys.argv[1]
    # run_accepted = input("About to run the pipeline with RUNID: {}. Do you accept? (y/n): ".format(RUNID))
    # run_accepted = run_accepted == 'y'
    # if run_accepted:
    #     main(RUNID)
    # else:
    #     print("Pipeline run cancelled.")
