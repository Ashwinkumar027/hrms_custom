import frappe

def execute():
    try:
        # 1. Create the Custom Field on Job Applicant
        cf_name = "Job Applicant-custom_original_applicant_id"
        if not frappe.db.exists("Custom Field", cf_name):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Job Applicant",
                "fieldname": "custom_original_applicant_id",
                "label": "Original Applicant ID",
                "fieldtype": "Data",
                "hidden": 1,
                "module": "HRMS custom"
            }).insert()
            print("Created Custom Field 'custom_original_applicant_id'.")
            
        # 2. Add the field to the Web Form
        wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
        field_exists = any(f.fieldname == "custom_original_applicant_id" for f in wf.web_form_fields)
        if not field_exists:
            wf.append("web_form_fields", {
                "fieldname": "custom_original_applicant_id",
                "fieldtype": "Data",
                "label": "Original Applicant ID",
                "hidden": 1
            })
            wf.save()
            print("Added 'custom_original_applicant_id' to Web Form.")

        # 3. Patch the API python file to send the correct parameter
        api_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/api/employee.py"
        with open(api_path, "r") as f:
            content = f.read()
            
        target_param = '"job_applicant": doc.name,'
        replacement_param = '"custom_original_applicant_id": doc.name,'
        
        if target_param in content:
            content = content.replace(target_param, replacement_param)
            with open(api_path, "w") as f:
                f.write(content)
            print("Patched employee.py API URL parameters.")
            
        # 4. Patch the Server Script to use the ID
        ss = frappe.get_doc("Server Script", "Merge Pre-Offer Form to Job Applicant")
        script = ss.script
        
        target_script = """existing = None
if doc.email_id:
    existing = frappe.db.get_value(
        "Job Applicant",
        {"email_id": doc.email_id, "name": ["!=", doc.name], "job_title": doc.job_title},
        "name"
    )
if not existing and doc.phone_number:
    existing = frappe.db.get_value(
        "Job Applicant",
        {"phone_number": doc.phone_number, "name": ["!=", doc.name], "job_title": doc.job_title},
        "name"
    )"""
    
        replacement_script = """existing = None

# Foolproof match using the exact ID captured from the URL
if doc.custom_original_applicant_id:
    existing = frappe.db.exists("Job Applicant", doc.custom_original_applicant_id)

# Fallback (just in case they use an old link)
if not existing and doc.email_id:
    existing = frappe.db.get_value(
        "Job Applicant",
        {"email_id": doc.email_id, "name": ["!=", doc.name], "job_title": ["is", "set"]},
        "name"
    )"""

        if target_script in script:
            script = script.replace(target_script, replacement_script)
            ss.script = script
            ss.save()
            print("Patched Merge Server Script.")

        frappe.db.commit()
        print("All patches applied successfully!")

    except Exception as e:
        print(f"Error: {e}")
