import re
import os

file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/hooks.py"
with open(file_path, "r") as f:
    content = f.read()

# Find the Server Script fixture list and add the new script to it
target = "'Notify HR when Employee UPDATES a field', 'naming series in emp', 'Notify Manager - Employee Onboarding Assigned'"
replacement = "'Notify HR when Employee UPDATES a field', 'naming series in emp', 'Notify Manager - Employee Onboarding Assigned', 'Interview Feedback Notification'"

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Successfully added Interview Feedback Notification to hooks.py fixtures!")
else:
    print("Could not find the target string in hooks.py")
