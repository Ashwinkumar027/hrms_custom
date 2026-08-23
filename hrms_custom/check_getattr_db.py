import frappe

def execute():
    try:
        print("--- Checking Server Scripts for 'getattr' ---")
        server_scripts = frappe.db.sql("SELECT name FROM `tabServer Script` WHERE script LIKE '%getattr%'", as_dict=True)
        if server_scripts:
            for s in server_scripts:
                print(f"WARNING: Found 'getattr' in Server Script: {s.name}")
        else:
            print("Safe! No other Server Scripts contain 'getattr'.")

        print("\n--- Checking Client Scripts for 'getattr' ---")
        client_scripts = frappe.db.sql("SELECT name FROM `tabClient Script` WHERE script LIKE '%getattr%'", as_dict=True)
        if client_scripts:
            for c in client_scripts:
                print(f"Found 'getattr' in Client Script (JS): {c.name}")
        else:
            print("Safe! No Client Scripts contain 'getattr'.")

    except Exception as e:
        print(f"Error: {e}")
