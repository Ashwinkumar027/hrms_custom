import frappe

def execute():
    try:
        api_path = "/home/ashwinkumark_quanti/frappe/my-bench/apps/hrms_custom/hrms_custom/overrides/employee_onboarding.py"
        with open(api_path, "r") as f:
            content = f.read()

        # Fix 1: Stop child.insert() and use self.append()
        # Look for the child.insert block
        target_child = """            # Auto-populate the activities tracking child table
            child = frappe.new_doc("Employee Boarding Activity")
            child.parent = self.name
            child.parenttype = "Employee Onboarding"
            child.parentfield = "activities"
            child.activity_name = subject
            child.custom_ticket_id = ticket.name
            child.custom_status = "Pending"
            
            # Fetch assigned user from ToDo if auto-assigned
            todos = frappe.get_all("ToDo", filters={"reference_type": "HD Ticket", "reference_name": ticket.name}, fields=["allocated_to"])
            user_email = None
            if todos:
                child.user = todos[0].allocated_to
                user_email = frappe.db.get_value("User", child.user, "email")
                
            child.insert(ignore_permissions=True)"""

        replacement_child = """            # Fetch assigned user from ToDo if auto-assigned
            todos = frappe.get_all("ToDo", filters={"reference_type": "HD Ticket", "reference_name": ticket.name}, fields=["allocated_to"])
            assigned_user = todos[0].allocated_to if todos else None
            user_email = frappe.db.get_value("User", assigned_user, "email") if assigned_user else None

            # Auto-populate the activities tracking child table using self.append
            self.append("activities", {
                "activity_name": subject,
                "custom_ticket_id": ticket.name,
                "custom_status": "Pending",
                "user": assigned_user
            })"""

        if target_child in content:
            content = content.replace(target_child, replacement_child)
            print("Patched child table logic.")
        else:
            print("Could not find target child logic!")

        # Fix 2: on_update infinite loop prevention
        target_on_update = """    def on_update(self):
        if hasattr(super(), "on_update"): super().on_update()
        if self.workflow_state == "Onboarding In Progress":
            self._create_onboarding_tickets()"""
            
        replacement_on_update = """    def on_update(self):
        if hasattr(super(), "on_update"): super().on_update()
        if self.workflow_state == "Onboarding In Progress" and not self.flags.tickets_created:
            self.flags.tickets_created = True
            # Clear existing activities to prevent duplicates if any leftover
            self.set("activities", [])
            self._create_onboarding_tickets()
            # Save the newly appended activities safely
            self.save(ignore_permissions=True)"""
            
        if target_on_update in content:
            content = content.replace(target_on_update, replacement_on_update)
            print("Patched on_update logic.")
        else:
            print("Could not find on_update logic!")

        # Fix 3: ID Card Image Attachment
        target_sendmail = """        frappe.sendmail(
            recipients=[designer_email],
            cc=hr_emails,
            sender=get_hr_sender(),
            subject=subject,
            message=message,
            reference_doctype="Employee Onboarding",
            reference_name=self.name,
        )"""

        replacement_sendmail = """        attachments = []
        if self.custom_candidate_passport_size_image_for_id_card:
            attachments.append({"file_url": self.custom_candidate_passport_size_image_for_id_card})

        frappe.sendmail(
            recipients=[designer_email],
            cc=hr_emails,
            sender=get_hr_sender(),
            subject=subject,
            message=message,
            reference_doctype="Employee Onboarding",
            reference_name=self.name,
            attachments=attachments
        )"""

        if target_sendmail in content:
            content = content.replace(target_sendmail, replacement_sendmail)
            print("Patched ID card sendmail logic.")
        else:
            print("Could not find sendmail logic!")

        with open(api_path, "w") as f:
            f.write(content)
            
        print("Done rewriting employee_onboarding.py")
        
    except Exception as e:
        print(f"Error: {e}")
