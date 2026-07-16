import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Claim ID", "fieldname": "name", "fieldtype": "Link", "options": "TA Reimbursement Claim", "width": 150},
		{"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{"label": "Designation", "fieldname": "designation", "fieldtype": "Data", "width": 150},
		{"label": "Office Location", "fieldname": "office_location", "fieldtype": "Data", "width": 150},
		{"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": "Reporting Manager", "fieldname": "reporting_manager", "fieldtype": "Link", "options": "Employee", "width": 150},
		{"label": "Claim Month", "fieldname": "claim_month", "fieldtype": "Data", "width": 100},
		{"label": "Claim Year", "fieldname": "claim_year", "fieldtype": "Data", "width": 80},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency", "width": 120},
		{"label": "Remarks", "fieldname": "remarks", "fieldtype": "Small Text", "width": 200},
		{"label": "Last Updated", "fieldname": "modified", "fieldtype": "Datetime", "width": 150},
	]


def get_data(filters):
	conditions = ["trc.docstatus != 2"]
	values = {}

	if filters.get("employee"):
		conditions.append("trc.employee = %(employee)s")
		values["employee"] = filters["employee"]

	if filters.get("department"):
		conditions.append("trc.department = %(department)s")
		values["department"] = filters["department"]

	if filters.get("claim_month"):
		conditions.append("trc.claim_month = %(claim_month)s")
		values["claim_month"] = filters["claim_month"]

	if filters.get("claim_year"):
		conditions.append("trc.claim_year = %(claim_year)s")
		values["claim_year"] = filters["claim_year"]

	if filters.get("status"):
		conditions.append("trc.status = %(status)s")
		values["status"] = filters["status"]

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			trc.name, trc.employee, trc.employee_name, trc.designation,
			trc.office_location, trc.department, trc.reporting_manager,
			trc.claim_month, trc.claim_year, trc.status, trc.total_amount,
			trc.remarks, trc.modified
		FROM `tabTA Reimbursement Claim` trc
		WHERE {where_clause}
		ORDER BY trc.claim_year DESC, trc.claim_month DESC, trc.modified DESC
	"""

	return frappe.db.sql(query, values, as_dict=True)
