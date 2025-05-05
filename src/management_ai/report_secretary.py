from datetime import datetime, timedelta
from prefect_data_getters.stores.rag_man import MultiSourceSearcher
from management_ai.reporting import run_report, write_reports

from prefect_data_getters.utilities.people import HYPERION,person

from prefect_data_getters.utilities.timing import print_human_readable_delta

searcher = MultiSourceSearcher()
def generate_secratary_report(days_ago: int = 2):
    """ Main function to generate bi weekly reports."""
    #  for p in HYPERION:
    start_date = get_workdays_ago(days_ago)
    report = run_report(
        docs=_get_documents(from_date=start_date, to_date=datetime.now()),
        report_message=_get_report_query(),
    )
    write_reports([report], f"Secretary notes from {(start_date).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}", "secretary")
    return report


def get_workdays_ago(days):
    current_date = datetime.now()
    workdays_count = 0
    while workdays_count < days:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:  # Monday to Friday are considered workdays
            workdays_count += 1
    return current_date
    
def _get_report_query():
    return f"""
You are my secratary and I need you to do exhaustive research about the past 48 hours.
Todays date is {datetime.now().strftime("%Y-%m-%d")}.
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

def _get_documents(from_date = datetime.now()-timedelta(days=2), to_date=datetime.now()):

    
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

    all_docs =  jiras + emails + slacks + bbs
    return all_docs


if __name__ == "__main__":
    generate_secratary_report()