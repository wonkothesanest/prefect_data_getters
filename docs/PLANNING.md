We have made several changes to the exporting logic for the following files.  I need you symantically check each of the files agains the git master version of their corresponding file (not the same file path). 

When you find differences in logic that might break the old logic I want you to create a plan to update the current version in order to make it more like the master version, but of course I want to keep the updated style of the exporter.

It is perfectly acceptable that no changes need to be made to the existing file and you may move on to the next one. 

Here are the new files and the master versions of the files to check against

Calendar:
[text](../src/prefect_data_getters/exporters/calendar_exporter.py)
master version: [text](../src/prefect_data_getters/exporters/google_calendar/__init__.py)

Slack:
[text](../src/prefect_data_getters/exporters/slack_exporter.py)
[text](../src/prefect_data_getters/exporters/slack/__init__.py)

Slab:
[text](../src/prefect_data_getters/exporters/slab_exporter.py)
[text](../src/prefect_data_getters/exporters/slab/__init__.py)

Gmail: 
[text](../src/prefect_data_getters/exporters/gmail_exporter.py)
[text](../src/prefect_data_getters/exporters/gmail/__init__.py)

Jira: 
[text](../src/prefect_data_getters/exporters/jira_exporter.py)
[text](../src/prefect_data_getters/exporters/jira/__init__.py)

Write each plan into the Tasks.md file before starting on the work.
