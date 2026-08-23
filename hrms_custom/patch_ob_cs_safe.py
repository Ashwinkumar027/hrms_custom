import frappe

def execute():
    try:
        scripts = frappe.get_all("Client Script", filters={"dt": "Employee Onboarding"}, fields=["name"])
        for s in scripts:
            cs = frappe.get_doc("Client Script", s.name)
            if "frm.set_df_property('activities', 'hidden', 1);" in cs.script:
                cs.script = cs.script.replace("frm.set_df_property('activities', 'hidden', 1);", "// frm.set_df_property('activities', 'hidden', 1); // Unhidden to show activities")
                cs.save()
                print(f"Successfully unhidden the activities table in Client Script: {s.name}!")
        frappe.db.commit()
    except Exception as e:
        print(f"Error: {e}")
