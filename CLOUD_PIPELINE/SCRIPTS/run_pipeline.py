import sys
import os

from azure.storage.blob import BlobServiceClient
import json

from CLOUD_PIPELINE.SCRIPTS.A_source_crawling_jina.orchestrator import main as source_crawling_jina
from CLOUD_PIPELINE.SCRIPTS.B_source_crawling_ddgs import main as source_crawling_ddgs
from CLOUD_PIPELINE.SCRIPTS.C_deduplicate_raw_articles import main as deduplicate_raw_articles
from CLOUD_PIPELINE.SCRIPTS.D_relevance_check.orchestrator import main as relevance_check
from CLOUD_PIPELINE.SCRIPTS.E_read_relevant_articles import main as read_relevant_articles
from CLOUD_PIPELINE.SCRIPTS.F_summarize_relevant_articles.orchestrator import main as summarize_relevant_articles
from CLOUD_PIPELINE.SCRIPTS.G_embed_relevant_summaries import main as embed_relevant_summaries

from dotenv import load_dotenv

from datetime import datetime
import time 

from argparse import ArgumentParser


load_dotenv('/home/xavaki/DAMM/linkedin_gen_contents/.env')

def main(RUNID: str, resume_step: str = None):

    if not resume_step:
        print("Starting fresh pipeline with RUNID: {}".format(RUNID))
    else:
        print("Resuming pipeline from step: {} with RUNID: {}".format(resume_step, RUNID))


    pipeline = [
        "source_crawling_jina",
        "source_crawling_ddgs",
        "deduplicate_raw_articles",
        "relevance_check",
        "read_relevant_articles",
        "summarize_relevant_articles",
        "embed_relevant_summaries"
    ]

    # todo 
    allowed_resume_steps = [
        "source_crawling_ddgs",
        "deduplicate_raw_articles",
        "read_relevant_articles",
        "embed_relevant_summaries",
    ]
    if resume_step and resume_step not in allowed_resume_steps:
        raise ValueError(f"Invalid resume step: {resume_step}. Must be one of {allowed_resume_steps}.")
    
    for step in pipeline:

        if resume_step and step != resume_step:
            print(f"Skipping step: {step} (resuming from {resume_step})")
            continue

        resume_step = None 

        print(step.replace("_", " ").upper())
        try:
            eval(step)(RUNID)
        except Exception as e:
            return False, step, e
        print("#############\n\n")

    return True, None, None

if __name__ == "__main__":

    # create argument parser
    parser = ArgumentParser(description="Run the cloud pipeline with a specific RUNID.")
    parser.add_argument("--run_location", type=str, default="local", help="Location where the pipeline is run (e.g., 'local', 'azure').")
    # resume step option (default is None)
    parser.add_argument("--resume_step", type=str, default=None, help="Step to resume the pipeline from (e.g., 'source_crawling_jina', 'source_crawling_ddgs', etc.). If None, the pipeline will start from the beginning.")
    args = parser.parse_args()

    run_location = args.run_location
    resume_step = args.resume_step
    print(f"Run location: {run_location} | Resume step: {resume_step}")

    blob_service_client = BlobServiceClient.from_connection_string(os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING"))
    runs_metadata_blob = blob_service_client.get_blob_client(container="runs-metadata", blob="runs_metadata.json")
    runs_metadata = json.loads(runs_metadata_blob.download_blob().readall())

    runs_metadata.sort(key=lambda x: int(x.get("RUNID", "").split("_")[-1]), reverse=False)
    last_run = runs_metadata[-1]
    last_run_status = last_run.get("status", "unknown")
    if last_run_status == "failed":
        print(f"Last run {last_run['RUNID']} failed at step {last_run.get("failed_step")} with error: {last_run.get('error', 'No error message provided')}.")
        resume = input(f"Do you want to resume the pipeline from the last failed step {last_run.get("failed_step")}? (y/n): ").strip().lower()
        if resume == 'y':
            run_id = last_run['RUNID']
            resume_step = last_run.get("failed_step")
        else:
            print("Starting a new run.")
            run_id = f"RUNID_{int(last_run['RUNID'].split('_')[-1]) + 1}"

    start_time = time.time()
    pipeline_success, failed_step, error = main(run_id, resume_step=resume_step)
    run_duration = time.time() - start_time

    pipeline_finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if pipeline_success:
        print("Pipeline completed successfully for RUNID: {}".format(run_id))
        runs_metadata.append({
            "RUNID": run_id,
            "status": "success",
            "run_location": run_location,
            "run_duration": run_duration,
            "pipeline_finish_time": pipeline_finish_time
        })
        runs_metadata_blob.upload_blob(json.dumps(runs_metadata), overwrite=True)
    else:
        print("Pipeline failed at step: {} with error: {}".format(failed_step, error))
        runs_metadata.append({
            "RUNID": run_id,
            "status": "failed",
            "failed_step": failed_step,
            "error": str(error),
            "run_location": run_location,
            "run_duration": run_duration,
            "pipeline_finish_time": pipeline_finish_time
        })
        runs_metadata_blob.upload_blob(json.dumps(runs_metadata), overwrite=True)

    # RUNID = sys.argv[1]
    # run_accepted = input("About to run the pipeline with RUNID: {}. Do you accept? (y/n): ".format(RUNID))
    # run_accepted = run_accepted == 'y'
    # if run_accepted:
    #     main(RUNID)
    # else:
    #     print("Pipeline run cancelled.")
