import re

file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/hooks.py"
with open(file_path, "r") as f:
    content = f.read()

# Use regex to replace the Client Script and Server Script dictionaries entirely
# We'll match from {"dt": "Client Script", ... to },
client_script_pattern = re.compile(r'\{\s*"dt":\s*"Client Script",\s*"filters":\s*\[\["name",\s*"in",\s*\[.*?\]\]\],\s*\},', re.DOTALL)
server_script_pattern = re.compile(r'\{\s*"dt":\s*"Server Script",\s*"filters":\s*\[\["name",\s*"in",\s*\[.*?\]\]\],\s*\},', re.DOTALL)

client_script_replacement = '{\n        "dt": "Client Script",\n        "filters": [["module", "=", "HRMS custom"]],\n    },'
server_script_replacement = '{\n        "dt": "Server Script",\n        "filters": [["module", "=", "HRMS custom"]],\n    },'

if client_script_pattern.search(content):
    content = client_script_pattern.sub(client_script_replacement, content)
    print("Replaced Client Script filters")
else:
    print("Could not find Client Script filters to replace")

if server_script_pattern.search(content):
    content = server_script_pattern.sub(server_script_replacement, content)
    print("Replaced Server Script filters")
else:
    print("Could not find Server Script filters to replace")

with open(file_path, "w") as f:
    f.write(content)
print("Finished patching hooks.py")
