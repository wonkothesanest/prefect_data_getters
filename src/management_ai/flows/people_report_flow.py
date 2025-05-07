from datetime import datetime, timedelta
from prefect import flow, task
import sys
import os

# Add the parent directory to the path so we can import from management_ai
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect_data_getters.utilities.people import HYPERION, person
from management_ai.reporting import run_report, write_reports

@task
def get_documents(p, from_date, to_date):
    """Task to get documents for a person"""
    from management_ai.report_people import _get_documents
    return _get_documents(p, from_date=from_date, to_date=to_date)

@task
def get_report_query(p):
    """Task to get the report query for a person"""
    from management_ai.report_people import _get_report_query
    return _get_report_query(p)

@task
def generate_person_report(p, from_date, to_date):
    """Task to generate a report for a single person"""
    docs = get_documents(p, from_date, to_date)
    query = get_report_query(p)
    report = run_report(docs=docs, report_message=query)
    return f"{p.first} {p.last} report from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}\n\n{report}"

@flow(name="People Report Flow")
def people_report_flow(
    weeks_back: int = 2,
    person_name: str = "",
    all_people: bool = False
):
    """
    Flow to generate people reports
    
    Args:
        weeks_back: Number of weeks to look back for data (default: 2)
        person_name: Name of specific person to generate report for (default: "", which means all people)
        all_people: Whether to generate reports for all people (default: False)
    """
    
    now = datetime.now()
    from_date = now - timedelta(weeks=weeks_back)
    to_date = now
    
    all_reports = []
    
    if person_name and person_name.strip() and not all_people:
        # Generate report for a specific person
        for p in HYPERION:
            if p.first.lower() == person_name.lower() or f"{p.first} {p.last}".lower() == person_name.lower():
                report = generate_person_report(p, from_date, to_date)
                all_reports.append(report)
                break
    else:
        # Generate reports for all people
        for p in HYPERION:
            report = generate_person_report(p, from_date, to_date)
            all_reports.append(report)
    
    # Write individual reports
    if all_reports:
        write_reports(all_reports, f"People from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}", "people")
    
    return "People reports generated successfully"

if __name__ == "__main__":
    people_report_flow()