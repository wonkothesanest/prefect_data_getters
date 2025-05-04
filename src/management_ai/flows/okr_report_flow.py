from datetime import datetime
from prefect import flow, task
import sys
import os

# Add the parent directory to the path so we can import from management_ai
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from management_ai.agents.report_template_okrs import okrs_2025_q2
from management_ai.reporting import write_reports
from prefect_data_getters.utilities.timing import print_human_readable_delta

@task
def run_okr_report(okr):
    """Task to run a single OKR report"""
    from datetime import datetime
    from management_ai.report_okrs import graph
    
    start_time = datetime.now()
    report = None
    
    # Import here to avoid circular imports
    from management_ai.report_okrs import status_update_prompt
    
    for event in graph.stream({"messages": [], "okr": okr, "prompt": status_update_prompt(okr)}, stream_mode="values"):
        if(event.get("report", None)):
            report = event.get('report')
    
    end_time = datetime.now()
    print_human_readable_delta(start_time, end_time)
    
    return {"okr": str(okr), "report": report}

@flow(name="OKR Report Flow")
def okr_report_flow(quarter: str = "current"):
    """
    Flow to generate OKR reports
    
    Args:
        quarter: Which quarter to generate reports for (default: "current")
    """
    # In a real implementation, you would select different OKRs based on the quarter parameter
    # For now, we'll just use the Q2 2025 OKRs
    
    all_reports = []
    for okr in okrs_2025_q2:
        report_result = run_okr_report(okr)
        all_reports.append(report_result)
    
    # Format reports for writing
    formatted_reports = [f"{r['okr']}\n\n{r['report']}" for r in all_reports]
    
    # Write reports to the okr subfolder
    write_reports(formatted_reports, "OKR_Reports", "okr")
    
    return "OKR reports generated successfully"

if __name__ == "__main__":
    okr_report_flow()