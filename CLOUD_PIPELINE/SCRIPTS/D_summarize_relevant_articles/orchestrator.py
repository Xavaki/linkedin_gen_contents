from CLOUD_PIPELINE.SCRIPTS.D_summarize_relevant_articles.A_create_batch_files import main as create_batch_files
from CLOUD_PIPELINE.SCRIPTS.D_summarize_relevant_articles.B_submit_batch_jobs import main as submit_batch_jobs
from CLOUD_PIPELINE.SCRIPTS.D_summarize_relevant_articles.C_retrieve_output_files import main as retrieve_output_files
from CLOUD_PIPELINE.SCRIPTS.D_summarize_relevant_articles.D_process_outputs import main as process_outputs

from time import sleep
import sys

TASK_NAME = "article_summarization_v0"

def main(RUNID: str):
    print(f"Starting {TASK_NAME} orchestrator with RUNID: {RUNID}")

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
    RUNID = sys.argv[1]
    main(RUNID)

