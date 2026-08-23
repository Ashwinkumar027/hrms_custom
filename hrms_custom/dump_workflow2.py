import frappe

def execute():
    try:
        # Fetch the exact script name based on a fuzzy search
        scripts = frappe.db.sql("SELECT name, script FROM `tabServer Script` WHERE script LIKE '%job_requisition_workflow_emails%' OR name LIKE '%job_requisition_workflow_emails%'", as_dict=True)
        
        if scripts:
            exact_name = scripts[0].name
            script_content = scripts[0].script
            print(f"Found Server Script. Exact Name: '{exact_name}'")
            
            file_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/dumped_script.py"
            with open(file_path, "w") as f:
                f.write(script_content)
                
            print(f"Successfully dumped script to {file_path}")
        else:
            print("Server Script not found in DB at all.")
    except Exception as e:
        print(f"Error: {e}")
