import os
file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/hooks.py"
with open(file_path, "r") as f:
    content = f.read()

if '"Server Script"' not in content and "'Server Script'" not in content:
    print("Server Script is NOT in fixtures. Adding it...")
    # Find the fixtures array and append it. We'll just replace 'fixtures = [' with 'fixtures = [\n    "Server Script",'
    if "fixtures = [" in content:
        content = content.replace("fixtures = [", 'fixtures = [\n    "Server Script",')
        with open(file_path, "w") as f:
            f.write(content)
        print("Successfully added Server Script to fixtures.")
    else:
        print("Could not find fixtures array in hooks.py")
else:
    print("Server Script is already in fixtures.")
