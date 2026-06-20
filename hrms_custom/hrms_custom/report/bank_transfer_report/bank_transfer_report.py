import calendar
import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"fieldname": "beneficiary_name",           "label": "Beneficiary Name",                    "fieldtype": "Data",     "width": 200},
        {"fieldname": "beneficiary_account_number", "label": "Beneficiary Account Number",           "fieldtype": "Data",     "width": 190},
        {"fieldname": "ifsc",                       "label": "IFSC",                                 "fieldtype": "Data",     "width": 140},
        {"fieldname": "transaction_type",           "label": "Transaction Type",                     "fieldtype": "Data",     "width": 130},
        {"fieldname": "debit_account_number",       "label": "Debit Account Number",                 "fieldtype": "Data",     "width": 190},
        {"fieldname": "transaction_date",           "label": "Transaction Date",                     "fieldtype": "Data",     "width": 130},
        {"fieldname": "amount",                     "label": "Amount",                               "fieldtype": "Currency", "width": 140},
        {"fieldname": "currency",                   "label": "Currency",                             "fieldtype": "Data",     "width": 80},
        {"fieldname": "beneficiary_email",          "label": "Beneficiary Email ID",                 "fieldtype": "Data",     "width": 210},
        {"fieldname": "remarks",                    "label": "Remarks",                              "fieldtype": "Data",     "width": 200},
        {"fieldname": "custom_header_1",            "label": "Employee ID",                          "fieldtype": "Data",     "width": 130},
        {"fieldname": "custom_header_2",            "label": "Department",                           "fieldtype": "Data",     "width": 160},
        {"fieldname": "custom_header_3",            "label": "Salary Slip",                          "fieldtype": "Data",     "width": 180},
        {"fieldname": "custom_header_4",            "label": "Payroll Entry",                        "fieldtype": "Data",     "width": 170},
        {"fieldname": "custom_header_5",            "label": "Slip Status",                          "fieldtype": "Data",     "width": 110},
    ]


def get_data(filters):
    conditions, values = get_conditions(filters)

    salary_slips = frappe.db.sql("""
        SELECT
            ss.name          AS salary_slip,
            ss.employee      AS employee,
            ss.employee_name AS employee_name,
            ss.net_pay       AS net_pay,
            ss.start_date    AS start_date,
            ss.end_date      AS end_date,
            ss.payroll_entry AS payroll_entry,
            ss.department    AS department,
            ss.docstatus     AS docstatus
        FROM
            `tabSalary Slip` ss
        WHERE
            ss.docstatus IN (0, 1)
            {conditions}
        ORDER BY
            ss.employee_name ASC, ss.start_date DESC
    """.format(conditions=conditions), values=values, as_dict=True)

    if not salary_slips:
        return []

    # Fetch all employee bank details in one query
    employee_ids = list(set(ss.employee for ss in salary_slips))
    employee_map = get_employee_bank_details(employee_ids)

    # Format transaction date DD/MM/YYYY
    transaction_date_formatted = format_date_ddmmyyyy(filters.get("transaction_date"))
    debit_account = filters.get("debit_account_number") or ""

    status_map = {0: "Draft", 1: "Submitted"}

    data = []
    for ss in salary_slips:
        emp = employee_map.get(ss.employee, {})

        beneficiary_name = emp.get("custom_name_as_per_bank") or ss.employee_name or ""
        email            = emp.get("prefered_email") or emp.get("company_email") or ""
        txn_type         = emp.get("custom_payment_type") or ""
        bank_ac          = emp.get("bank_ac_no") or ""
        ifsc             = emp.get("custom_ifsc_code") or ""
        bank_name        = emp.get("bank_name") or ""

        # Remarks: "Salary for June 2026"
        if ss.start_date:
            month_name = calendar.month_name[ss.start_date.month]
            remarks = "Salary for {} {}".format(month_name, ss.start_date.year)
        else:
            remarks = "Salary Payment"

        data.append({
            "beneficiary_name":           beneficiary_name,
            "beneficiary_account_number": bank_ac,
            "ifsc":                       ifsc,
            "transaction_type":           txn_type,
            "debit_account_number":       debit_account,
            "transaction_date":           transaction_date_formatted,
            "amount":                     ss.net_pay or 0,
            "currency":                   "INR",
            "beneficiary_email":          email,
            "remarks":                    remarks,
            "custom_header_1":            ss.employee or "",
            "custom_header_2":            ss.department or "",
            "custom_header_3":            ss.salary_slip or "",
            "custom_header_4":            ss.payroll_entry or "",
            "custom_header_5":            status_map.get(ss.docstatus, ""),
        })

    return data


def get_employee_bank_details(employee_ids):
    if not employee_ids:
        return {}

    employees = frappe.db.sql("""
        SELECT
            name,
            custom_name_as_per_bank,
            bank_ac_no,
            custom_ifsc_code,
            custom_payment_type,
            bank_name,
            company_email,
            prefered_email
        FROM `tabEmployee`
        WHERE name IN ({placeholders})
    """.format(
        placeholders=", ".join(["%s"] * len(employee_ids))
    ), tuple(employee_ids), as_dict=True)

    return {emp.name: emp for emp in employees}


def get_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("company"):
        conditions += " AND ss.company = %(company)s"
        values["company"] = filters["company"]

    if filters.get("from_date"):
        conditions += " AND ss.start_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions += " AND ss.end_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]

    if filters.get("payroll_entry"):
        conditions += " AND ss.payroll_entry = %(payroll_entry)s"
        values["payroll_entry"] = filters["payroll_entry"]

    if filters.get("docstatus") == "Draft":
        conditions += " AND ss.docstatus = 0"
    elif filters.get("docstatus") == "Submitted":
        conditions += " AND ss.docstatus = 1"

    return conditions, values


def format_date_ddmmyyyy(date_value):
    if not date_value:
        return ""
    date_str = str(date_value)
    # Input from Frappe is YYYY-MM-DD
    if "-" in date_str:
        parts = date_str.split("-")
        if len(parts) == 3:
            return "{}/{}/{}".format(parts[2], parts[1], parts[0])
    return date_str
