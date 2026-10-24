import calendar
import io
import json
from typing import Any, Dict, List, Optional
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


IDFC_COLUMNS = [
    ("Beneficiary Name", "Enter beneficiary name.\nMANDATORY", 25),
    ("Beneficiary Account Number", "Enter beneficiary Account Number.\nMANDATORY", 25),
    ("IFSC", "Enter IFSC code.\nMANDATORY (Except for IFT)", 15),
    ("Transaction Type", "Enter value IFT/NEFT/RTGS.\nMANDATORY", 18),
    ("Debit Account Number", "Enter debit Account number.\nMANDATORY", 22),
    ("Transaction Date", "Enter Transaction date in DD/MM/YYYY format.\nMANDATORY", 18),
    ("Amount", "Enter Transaction amount with maximum two decimal places.\nMANDATORY", 15),
    ("Currency", "Enter Currency INR for INR transactions.\nMANDATORY", 10),
    ("Beneficiary Email ID", "Enter email id for email alert\nOPTIONAL", 25),
    ("Remarks", "Enter Remarks.\nOPTIONAL", 25),
    ("Custom Header – 1", "Enter customer reference text\nOPTIONAL", 18),
    ("Custom Header – 2", "Enter customer reference text\nOPTIONAL", 18),
    ("Custom Header – 3", "Enter customer reference text\nOPTIONAL", 18),
    ("Custom Header – 4", "Enter customer reference text\nOPTIONAL", 18),
    ("Custom Header – 5", "Enter customer reference text\nOPTIONAL", 18),
]


@frappe.whitelist()
def resolve_company_debit_account(company: Optional[str] = None) -> str:
    """
    Retrieves the company's designated IDFC Bank Corporate Account Number.
    """
    # 1. Check AP Automation Settings if installed
    try:
        if frappe.db.exists("DocType", "AP Automation Settings"):
            settings = frappe.get_single("AP Automation Settings")
            if getattr(settings, "default_bank_account", None):
                ba = frappe.db.get_value("Bank Account", settings.default_bank_account, ["bank_account_no", "bank"], as_dict=True)
                if ba and ba.get("bank_account_no"):
                    return str(ba["bank_account_no"]).strip()
    except Exception:
        pass

    # 2. Check Bank Account linked to Company where bank has 'IDFC'
    if company:
        ba_idfc = frappe.db.sql("""
            SELECT bank_account_no FROM `tabBank Account`
            WHERE company = %s AND (bank LIKE '%%IDFC%%' OR bank_account_no IS NOT NULL)
            ORDER BY is_default DESC, creation DESC LIMIT 1
        """, (company,), as_dict=True)
        if ba_idfc and ba_idfc[0].get("bank_account_no"):
            return str(ba_idfc[0]["bank_account_no"]).strip()

    # 3. Default corporate IDFC Account for Quanticus
    return "10173678610"


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
            ss.docstatus     AS docstatus,
            ss.company       AS company
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
    company = filters.get("company") or (salary_slips[0].get("company") if salary_slips else None)
    default_debit_account = resolve_company_debit_account(company)
    debit_account = str(filters.get("debit_account_number") or default_debit_account).strip()

    status_map = {0: "Draft", 1: "Submitted"}

    data = []
    for ss in salary_slips:
        emp = employee_map.get(ss.employee, {})

        beneficiary_name = (emp.get("custom_name_as_per_bank") or ss.employee_name or "").strip().upper()
        email            = emp.get("prefered_email") or emp.get("company_email") or emp.get("personal_email") or ""
        bank_ac          = str(emp.get("bank_ac_no") or "").strip()
        
        # Resolve IFSC with fallback to standard ifsc_code
        ifsc = str(emp.get("custom_ifsc_code") or emp.get("ifsc_code") or "").strip().upper()

        # Compute Transaction Type per IDFC Banking Rules
        explicit_txn = str(emp.get("custom_payment_type") or "").strip().upper()
        if explicit_txn in ("IFT", "NEFT", "RTGS"):
            txn_type = explicit_txn
        elif ifsc.startswith("IDFB"):
            txn_type = "IFT"
        elif flt(ss.net_pay) >= 200000.0:
            txn_type = "RTGS"
        else:
            txn_type = "NEFT"

        # Remarks: "Salary for June 2026"
        if ss.start_date:
            month_name = calendar.month_name[ss.start_date.month]
            remarks = "Salary for {} {}".format(month_name, ss.start_date.year)[:30]
        else:
            remarks = "Salary Payment"

        data.append({
            "beneficiary_name":           beneficiary_name,
            "beneficiary_account_number": bank_ac,
            "ifsc":                       ifsc,
            "transaction_type":           txn_type,
            "debit_account_number":       debit_account,
            "transaction_date":           transaction_date_formatted,
            "amount":                     flt(ss.net_pay or 0, 2),
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
            employee_name,
            custom_name_as_per_bank,
            bank_ac_no,
            ifsc_code,
            custom_ifsc_code,
            custom_payment_type,
            bank_name,
            company_email,
            prefered_email,
            personal_email
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
        return getdate(nowdate()).strftime("%d/%m/%Y")
    date_str = str(date_value)
    if "-" in date_str:
        parts = date_str.split("-")
        if len(parts) == 3:
            return "{}/{}/{}".format(parts[2], parts[1], parts[0])
    return date_str


@frappe.whitelist()
def download_idfc_payroll_bank_excel(filters=None):
    """
    Direct endpoint: Generates and streams the official 15-column IDFC FIRST Bank
    Bulk Disbursal Excel Template ('IDFC Sheet') from Bank Transfer Report.
    """
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}
    elif not filters:
        filters = {}

    data = get_data(filters)
    if not data:
        frappe.throw(_("No salary slip records found for the selected filters."))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IDFC Sheet"
    ws.views.sheetView[0].showGridLines = True

    # Styling Palettes (Strictly matching Corporate Banking Spec)
    fill_row1 = PatternFill(start_color="B4C6E7", end_color="B4C6E7", fill_type="solid")  # Soft Blue
    fill_row2 = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")  # Pastel Blue
    font_row1 = Font(name="Calibri", size=10, bold=False, color="000000")
    font_row2 = Font(name="Calibri", size=10, italic=True, bold=False, color="000000")
    font_data = Font(name="Calibri", size=10, bold=False, color="000000")

    border_thin = Border(
        left=Side(style="thin", color="D3D3D3"),
        right=Side(style="thin", color="D3D3D3"),
        top=Side(style="thin", color="D3D3D3"),
        bottom=Side(style="thin", color="D3D3D3"),
    )

    ws.row_dimensions[1].height = 38.25
    ws.row_dimensions[2].height = 102.0

    # Row 1: Headers & Row 2: Instructions
    for col_idx, (col_name, col_instruction, col_width) in enumerate(IDFC_COLUMNS, start=1):
        # Row 1
        cell1 = ws.cell(row=1, column=col_idx, value=col_name)
        cell1.fill = fill_row1
        cell1.font = font_row1
        cell1.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell1.border = border_thin

        # Row 2
        cell2 = ws.cell(row=2, column=col_idx, value=col_instruction)
        cell2.fill = fill_row2
        cell2.font = font_row2
        cell2.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        cell2.border = border_thin

        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    # Row 3+: Data Rows
    current_row = 3
    for row in data:
        ws.row_dimensions[current_row].height = 20.0

        # Col 1: Beneficiary Name
        c1 = ws.cell(row=current_row, column=1, value=row.get("beneficiary_name", ""))
        c1.font = font_data
        c1.alignment = Alignment(horizontal="left", vertical="center")
        c1.border = border_thin

        # Col 2: Beneficiary Account Number (Text format to prevent scientific notation)
        c2 = ws.cell(row=current_row, column=2, value=str(row.get("beneficiary_account_number", "")).strip())
        c2.font = font_data
        c2.number_format = "@"
        c2.alignment = Alignment(horizontal="left", vertical="center")
        c2.border = border_thin

        # Col 3: IFSC
        c3 = ws.cell(row=current_row, column=3, value=str(row.get("ifsc", "")).strip().upper())
        c3.font = font_data
        c3.alignment = Alignment(horizontal="center", vertical="center")
        c3.border = border_thin

        # Col 4: Transaction Type (IFT / RTGS / NEFT)
        c4 = ws.cell(row=current_row, column=4, value=str(row.get("transaction_type", "")).strip().upper())
        c4.font = font_data
        c4.alignment = Alignment(horizontal="center", vertical="center")
        c4.border = border_thin

        # Col 5: Debit Account Number
        c5 = ws.cell(row=current_row, column=5, value=str(row.get("debit_account_number", "")).strip())
        c5.font = font_data
        c5.number_format = "@"
        c5.alignment = Alignment(horizontal="left", vertical="center")
        c5.border = border_thin

        # Col 6: Transaction Date
        c6 = ws.cell(row=current_row, column=6, value=row.get("transaction_date", ""))
        c6.font = font_data
        c6.alignment = Alignment(horizontal="center", vertical="center")
        c6.border = border_thin

        # Col 7: Amount
        c7 = ws.cell(row=current_row, column=7, value=flt(row.get("amount", 0.0)))
        c7.font = font_data
        c7.number_format = "0.00"
        c7.alignment = Alignment(horizontal="right", vertical="center")
        c7.border = border_thin

        # Col 8: Currency
        c8 = ws.cell(row=current_row, column=8, value="INR")
        c8.font = font_data
        c8.alignment = Alignment(horizontal="center", vertical="center")
        c8.border = border_thin

        # Col 9: Beneficiary Email ID
        c9 = ws.cell(row=current_row, column=9, value=row.get("beneficiary_email", ""))
        c9.font = font_data
        c9.alignment = Alignment(horizontal="left", vertical="center")
        c9.border = border_thin

        # Col 10: Remarks
        c10 = ws.cell(row=current_row, column=10, value=str(row.get("remarks", ""))[:30])
        c10.font = font_data
        c10.alignment = Alignment(horizontal="left", vertical="center")
        c10.border = border_thin

        # Col 11-15: Custom Headers (Internal audit reference)
        for ch_idx, key in enumerate(["custom_header_1", "custom_header_2", "custom_header_3", "custom_header_4", "custom_header_5"], start=11):
            c_custom = ws.cell(row=current_row, column=ch_idx, value=row.get(key, ""))
            c_custom.font = font_data
            c_custom.alignment = Alignment(horizontal="left", vertical="center")
            c_custom.border = border_thin

        current_row += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filebytes = output.getvalue()

    payroll_label = filters.get("payroll_entry") or filters.get("company") or "Payroll"
    clean_label = "".join(c for c in payroll_label if c.isalnum() or c in ("-", "_")).strip()
    filename = f"IDFC_Bank_Payroll_{clean_label}_{nowdate()}.xlsx"

    frappe.response["filename"] = filename
    frappe.response["filecontent"] = filebytes
    frappe.response["type"] = "binary"
