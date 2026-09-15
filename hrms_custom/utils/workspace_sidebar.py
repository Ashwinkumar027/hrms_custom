import frappe


def extend_bootinfo(bootinfo):
	"""Remove unwanted items (Roster, Shift Request, Overtime) from desk sidebar items for all users."""
	excluded_labels = {"Roster", "Shift Request", "Overtime", "Overtime Type", "Overtime Slip"}
	if hasattr(bootinfo, "workspace_sidebar_item") and isinstance(bootinfo.workspace_sidebar_item, dict):
		for key, sb in bootinfo.workspace_sidebar_item.items():
			if isinstance(sb, dict) and "items" in sb and isinstance(sb["items"], list):
				sb["items"] = [
					item
					for item in sb["items"]
					if item.get("label") not in excluded_labels
					and item.get("url") != "/hr/roster"
					and item.get("link_to") != "Shift Request"
				]


def sync_attendance_dashboard_and_sidebar():
	"""Run after migrate to enforce dashboard and sidebar requirements."""
	# 1. Remove Roster, Shift Request, Overtime from Workspace Sidebar 'Shift & Attendance'
	excluded_sidebar_labels = {"Roster", "Shift Request", "Overtime", "Overtime Type", "Overtime Slip"}
	if frappe.db.exists("Workspace Sidebar", "Shift & Attendance"):
		try:
			sidebar = frappe.get_doc("Workspace Sidebar", "Shift & Attendance")
			new_items = [
				item
				for item in sidebar.items
				if item.label not in excluded_sidebar_labels
				and getattr(item, "url", "") != "/hr/roster"
				and getattr(item, "link_to", "") != "Shift Request"
			]
			if len(new_items) != len(sidebar.items):
				sidebar.items = new_items
				sidebar.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.clear_cache(doctype="Workspace Sidebar")
		except Exception as e:
			frappe.log_error(str(e), "sync_attendance_dashboard_and_sidebar (sidebar)")

	# 2. Remove Shift Assignment Breakup, Timesheet Activity Breakup, Department wise Timesheet Hours from Dashboard 'Attendance'
	excluded_charts = {
		"Shift Assignment Breakup",
		"Timesheet Activity Breakup",
		"Department wise Timesheet Hours",
	}
	if frappe.db.exists("Dashboard", "Attendance"):
		try:
			dash = frappe.get_doc("Dashboard", "Attendance")
			new_charts = [c for c in dash.charts if c.chart not in excluded_charts]
			if len(new_charts) != len(dash.charts):
				dash.charts = new_charts
				dash.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.clear_cache(doctype="Dashboard")
		except Exception as e:
			frappe.log_error(str(e), "sync_attendance_dashboard_and_sidebar (dashboard)")

	# 3. Add Employee role to Report 'Monthly Attendance Sheet'
	if frappe.db.exists("Report", "Monthly Attendance Sheet"):
		try:
			rep = frappe.get_doc("Report", "Monthly Attendance Sheet")
			roles = [r.role for r in rep.roles]
			if "Employee" not in roles:
				rep.append("roles", {"role": "Employee"})
				rep.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.clear_cache(doctype="Report")
		except Exception as e:
			frappe.log_error(str(e), "sync_attendance_dashboard_and_sidebar (report)")
