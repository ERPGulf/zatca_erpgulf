import frappe

def execute():
    if not frappe.db.table_exists("Workspace Sidebar"):
        return
    frappe.db.sql("""
        UPDATE `tabWorkspace Sidebar`
        SET title = 'ZATCA by ERPGulf'
        WHERE title = 'ZATCA ERPGulf'
    """)