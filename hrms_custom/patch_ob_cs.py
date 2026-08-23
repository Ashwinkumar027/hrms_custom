import frappe

def execute():
    try:
        cs = frappe.get_doc("Client Script", "Employee Onboarding Workflow Helper")
        if "frm.set_df_property('activities', 'hidden', 1);" in cs.script:
            cs.script = cs.script.replace("frm.set_df_property('activities', 'hidden', 1);", "// frm.set_df_property('activities', 'hidden', 1); // Unhidden to show tickets")
            cs.save()
            frappe.db.commit()
            print("Successfully unhidden the activities table in Client Script!")
        else:
            print("Could not find the hidden property line in the script.")
    except Exception as e:
        print(f"Error: {e}")
