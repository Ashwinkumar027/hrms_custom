import os
import ast

file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/hooks.py"
with open(file_path, "r") as f:
    content = f.read()

# Let's just use string replacement that is resilient to formatting.
# We know the filters list is something like: ["name", "in", ["...", "...", "..."]]
# Let's search for "Notify Manager - Employee Onboarding Assigned"
if "Notify Manager - Employee Onboarding Assigned" in content:
    # Just replace it with itself + the new script
    target1 = "'Notify Manager - Employee Onboarding Assigned'"
    replacement1 = "'Notify Manager - Employee Onboarding Assigned', 'Interview Feedback Notification'"
    target2 = '"Notify Manager - Employee Onboarding Assigned"'
    replacement2 = '"Notify Manager - Employee Onboarding Assigned", "Interview Feedback Notification"'
    
    if target1 in content:
        content = content.replace(target1, replacement1)
    elif target2 in content:
        content = content.replace(target2, replacement2)
        
    with open(file_path, "w") as f:
        f.write(content)
    print("Successfully patched hooks.py!")
else:
    print("Could not find the marker string in hooks.py")
