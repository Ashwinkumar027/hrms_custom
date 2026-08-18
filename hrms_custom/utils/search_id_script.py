import frappe

def execute():
    scripts = frappe.get_all('Server Script', fields=['name', 'script'])
    for s in scripts:
        if s.script and 'ID Card Design Request' in s.script:
            print('Found in Server Script:', s.name)
            # Dump the script content
            with open('/home/ashwinkumark_quanti/frappe/my-bench/id_card_script.txt', 'w') as f:
                f.write(s.script)
