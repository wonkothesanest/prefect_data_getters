from datetime import datetime
from prefect import flow
import prefect

from prefect.artifacts import create_markdown_artifact
from management_ai.report_secretary import generate_secratary_report, get_workdays_ago


@flow(name="Secretary Report Flow")
def secretary_report_flow(workdays_back: int = 2):
    """
    Flow to generate secretary reports
    
    Args:
        workdays_back: Number of workdays to look back for data (default: 2)
    """

    logger = prefect.get_run_logger()
    logger.info(f"Generating secretary report for the last {workdays_back} workdays.")
    # Get the date that is workdays_back workdays ago
    from_date = get_workdays_ago(workdays_back)
    to_date = datetime.now()

    logger.info(f"From date: {from_date.strftime('%Y-%m-%d')}")
    logger.info(f"To date: {to_date.strftime('%Y-%m-%d')}")
    
    # Generate report
    report = generate_secratary_report(days_ago=workdays_back)
    
    # Store report as a Prefect artifact
    create_markdown_artifact(
        markdown=report,
        key="secretary-report",
        description=f"Secretary report from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
    )
    
    return "Secretary report generated successfully"

if __name__ == "__main__":
    secretary_report_flow()