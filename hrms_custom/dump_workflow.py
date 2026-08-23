import frappe
import os

def execute():
    try:
        script = frappe.db.get_value("Server Script", "job_requisition_workflow_emails", "script")
        
        file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/dumped_script.py"
        with open(file_path, "w") as f:
            f.write(script)
            
        print(f"Successfully dumped script to {file_path}")
    except Exception as e:
        print(f"Error: {e}")
