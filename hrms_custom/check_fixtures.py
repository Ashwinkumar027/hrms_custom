import os
file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/hooks.py"
with open(file_path, "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "fixtures" in line:
        print("".join(lines[i:i+15]))
        break
