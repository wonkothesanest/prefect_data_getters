from datetime import datetime, timedelta
from prefect_data_getters.stores.rag_man import MultiSourceSearcher
from reporting import run_report, write_reports

from prefect_data_getters.utilities.people import HYPERION,person

from prefect_data_getters.utilities.timing import print_human_readable_delta

searcher = MultiSourceSearcher()
def generate_people_reports():
    """ Main function to generate bi weekly reports."""
    all_reports = []
    for p in HYPERION:
        all_reports.append( run_report(
            docs=_get_documents(p),
            report_message=_get_report_query(p),
        ))
    write_reports(all_reports, "people")


def generate_people_reports_over_time():
    """To see progress over time, making weekly reports for each person then will need to enter them for analysis."""
    all_reports = []
    now = datetime.now()
    week1 = now - timedelta(weeks=1)
    week2 = now - timedelta(weeks=2)
    week3 = now - timedelta(weeks=3)
    week4 = now - timedelta(weeks=4)
    week5 = now - timedelta(weeks=5)
    
    dates = [
        (week5, week4),
        (week4, week3),
        (week3, week2),
        (week2, week1),
        (week1, now),
        ]
    for p in HYPERION[0:1]:
        for start,end in dates:
            print(f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
            r = run_report(
                docs=_get_documents(p, from_date=start, to_date=end),
                report_message=_get_report_query(p),
            )
            r = f"{p.first} {p.last} report from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}\n\n" + r
            all_reports.append(r)

        write_reports(all_reports, f"People {p.first}  from {week5.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    
def _get_report_query(p: person):
    return f"""
I want to know what a person on my team has been up to for the last couple of weeks.
Please use the research provided to write up a detailed report of what major contributions they have made.
Be sure to point out anything they have done that would deserve praise or commenation.
Person: {p.first} {p.last}

This short report should have the following sections to it
* Accomplishments
* What Problems they've solved
* Praise Worthy 
* Concerns

Also make a brief write up of a summary of everything you know about them. Keep it brief, your summary does not have to be exhaustive.

"""

def _get_documents(p:person,from_date = datetime.now()-timedelta(weeks=2), to_date=datetime.now()):

    
    jiras = searcher.search_by_username(
        index="jira_issues",
        username=p.first, 
        from_date=from_date,
        to_date=to_date,
        size=100
    )
    emails = searcher.search_by_username(
        index="email_messages",
        username=p.first, 
        from_date=from_date,
        to_date=to_date,
        size=50
    )
    slacks = searcher.search_by_username(
        index="slack_messages",
        username=p.first, 
        from_date=from_date,
        to_date=to_date,
        size=100
    )

    bbs = searcher.search_by_username(
        index="bitbucket_pull_requests",
        username=p.first, 
        from_date=from_date,
        to_date=to_date,
        size=30
    )

    all_docs =  jiras + emails + slacks + bbs
    return all_docs


if __name__ == "__main__":
    generate_people_reports_over_time()