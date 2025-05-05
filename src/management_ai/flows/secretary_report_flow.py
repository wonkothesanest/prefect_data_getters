from datetime import datetime, timedelta
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
import sys
import os

# Add the parent directory to the path so we can import from management_ai
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from management_ai.reporting import run_report, write_reports
from prefect_data_getters.stores.rag_man import MultiSourceSearcher

@task
def get_workdays_ago(days):
    """Task to get a date that is a specified number of workdays ago"""
    current_date = datetime.now()
    workdays_count = 0
    while workdays_count < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:  # Monday to Friday are considered workdays
            workdays_count += 1
    return current_date

@task
def get_documents(from_date, to_date):
    """Task to get documents for the secretary report"""
    searcher = MultiSourceSearcher()
    
    jiras = searcher.search_boring_search(
        index="jira_issues",
        from_date=from_date,
        to_date=to_date,
        size=100
    )
    
    emails = searcher.search_boring_search(
        index="email_messages",
        from_date=from_date,
        to_date=to_date,
        size=100
    )
    
    slacks = searcher.search_boring_search(
        index="slack_messages",
        from_date=from_date,
        to_date=to_date,
        size=200
    )
    
    bbs = searcher.search_boring_search(
        index="bitbucket_pull_requests",
        from_date=from_date,
        to_date=to_date,
        size=100
    )
    
    for e in emails:
        e.set_page_content(e.page_content[:4000])
    
    all_docs = jiras + emails + slacks + bbs
    return all_docs

@task
def get_report_query():
    """Task to get the report query for the secretary report"""
    return f"""
You are my secretary and I need you to do exhaustive research about the past 48 hours.
Today's date is {datetime.now().strftime("%Y-%m-%d")}.
You are my executive secretary, a highly advanced language model trained to manage my digital life.
Your responsibilities include managing my documents, emails, and recent information sources. You have access to:

Internal documentation
Incoming emails
Recent knowledge base articles
Jira issues
Slack messages
Bitbucket pull requests
You are to summarize the most important information from these sources and present it in a clear and concise manner.

Only documents and data from the last 48 hours are relevant and I will provide them to you.

Your Daily Briefing Should Include:
🧾 Summary of Noteworthy Events (Max 10 bullet points):
Provide a concise overview of recent happenings I should be aware of. Include any emergent trends, significant announcements, project updates, or unusual incidents.

✅ Action Items (Bullet list):
A list of clear, concise tasks I need to follow up on or delegate. Each item should include:

What needs to be done

Priority (High / Medium / Low)

Deadline (if any)

👥 Check-In Schedule (Table Format):
Outline who I need to check in with, when I should do it, and what we need to discuss. Use this format:


Person	Time to Check In	Topic(s) to Discuss
e.g. Burt	Today at 2PM	Unexpected spike in story uploads for the onboarding team
e.g. Adam	Tomorrow morning	API ingestion issues have been rising
"""

@flow(name="Secretary Report Flow")
def secretary_report_flow(workdays_back: int = 2):
    """
    Flow to generate secretary reports
    
    Args:
        workdays_back: Number of workdays to look back for data (default: 2)
    """
    # Get the date that is workdays_back workdays ago
    from_date = get_workdays_ago(workdays_back)
    to_date = datetime.now()
    
    # Get documents
    docs = get_documents(from_date, to_date)
    
    # Get report query
    query = get_report_query()
    
    # Generate report
    report = run_report(
        docs=docs,
        report_message=query,
    )
    
    # Create report title
    report_title = f"Secretary notes from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
    
    # Write report to file
    write_reports(
        [report],
        report_title,
        "secretary"
    )
    
    # Store report as a Prefect artifact
    create_markdown_artifact(
        markdown=report,
        key="secretary-report",
        description=f"Secretary report from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
    )
    
    return "Secretary report generated successfully"

if __name__ == "__main__":
    secretary_report_flow()