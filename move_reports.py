#!/usr/bin/env python3
import os
import re
import shutil

# Define report patterns and their target folders
report_patterns = [
    (r"reporting_people.*\.md", "reports/people"),
    (r"reporting_secratary_notes.*\.md", "reports/secretary"),
    (r"reporting_adhoc_report.*\.md", "reports/rag"),
    (r"reporting_\d{8}_\d{6}\.md", "reports/okr"),  # General reports with just timestamp
]

# Ensure target directories exist
for _, folder in report_patterns:
    os.makedirs(folder, exist_ok=True)

# Get all files in the root directory
files = [f for f in os.listdir('.') if os.path.isfile(f)]

# Move files to appropriate folders
moved_count = 0
for file in files:
    for pattern, folder in report_patterns:
        if re.match(pattern, file):
            source = file
            destination = os.path.join(folder, file)
            shutil.move(source, destination)
            print(f"Moved {source} to {destination}")
            moved_count += 1
            break

print(f"Moved {moved_count} report files to their appropriate folders")