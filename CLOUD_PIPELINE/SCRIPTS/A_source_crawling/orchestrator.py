from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.a_crawl_raw_articles_list import main as crawl_raw_articles_list
from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.A_create_batch_files import main as create_batch_files
from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.B_submit_batch_jobs import main as submit_batch_jobs
from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.C_retrieve_output_files import main as retrieve_output_files
from CLOUD_PIPELINE.SCRIPTS.A_source_crawling.D_process_outputs import main as process_outputs

from time import sleep
import sys

TASK_NAME = "source_parsing_v0"

def main(RUNID: str):
    print(f"Starting {TASK_NAME} orchestrator with RUNID: {RUNID}")
    crawl_raw_articles_list(RUNID)

    create_batch_files(RUNID)

    submit_batch_jobs(RUNID)

    print("Waiting for batch jobs to complete...")
    sleep(300)
    while True:

        batch_status = retrieve_output_files(RUNID)
        status = batch_status["status"]

        if status == "WAIT":
            wait_time = batch_status["wait_time"]
            print(f"Batch jobs still running. Waiting for {wait_time} seconds...")
            sleep(wait_time)

        elif status == "ALL_ERROR_END":
            raise Exception(f"All batch jobs for {TASK_NAME} ended with errors.")
        
        elif status == "ALL_COMPLETED_CONTINUE":
            break
    
    print("Batch jobs completed. Processing outputs...")
    process_outputs(RUNID)

if __name__ == "__main__":
    ...
    # RUNID = sys.argv[1]
    # main(RUNID)

