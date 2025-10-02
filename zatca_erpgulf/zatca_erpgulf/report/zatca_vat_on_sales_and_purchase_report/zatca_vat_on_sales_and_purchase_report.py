# import frappe

# def execute(filters=None):
#     columns, data = get_columns(), []

#     # -----------------------------
#     # 1. SALES VAT
#     # -----------------------------
#     sales_totals = get_sales_vat_totals(filters)

#     # Sales VAT heading
#     data.append({"category": "<b>Sales VAT</b>", "amount": None, "adjustment": None, "vat": None})

#     # Sales lines
#     data.append({
#         "category": "Standard rated sales",
#         "amount": sales_totals["Standard"]["amount"],
#         "adjustment": sales_totals["Standard"]["adjustment"],
#         "vat": sales_totals["Standard"]["vat"]
#     })
#     data.append({
#         "category": "Private Healthcare / Private Education sales to citizens",
#         "amount": sales_totals["HealthcareEdu"]["amount"],
#         "adjustment": sales_totals["HealthcareEdu"]["adjustment"],
#         "vat": sales_totals["HealthcareEdu"]["vat"]
#     })
#     data.append({
#         "category": "Zero rated domestic sales",
#         "amount": sales_totals["Zero Rated"]["amount"],
#         "adjustment": sales_totals["Zero Rated"]["adjustment"],
#         "vat": 0
#     })
#     data.append({
#         "category": "Exports",
#         "amount": sales_totals["Exports"]["amount"],
#         "adjustment": sales_totals["Exports"]["adjustment"],
#         "vat": sales_totals["Exports"]["vat"]
#     })
#     data.append({
#         "category": "Exempt sales",
#         "amount": sales_totals["Exempt"]["amount"],
#         "adjustment": sales_totals["Exempt"]["adjustment"],
#         "vat": 0
#     })

#     # Total Sales line
#     data.append({
#         "category": "<b>Total Sales</b>",
#         "amount": sum(v["amount"] for v in sales_totals.values()),
#         "adjustment": sum(v["adjustment"] for v in sales_totals.values()),
#         "vat": sum(v["vat"] for v in sales_totals.values()),
#     })

#     # -----------------------------
#     # 2. PURCHASE VAT
#     # -----------------------------
#     purchase_totals = get_purchase_vat_totals(filters)

#     # Empty row for spacing
#     data.append({"category": "", "amount": None, "adjustment": None, "vat": None})

#     # Purchase VAT heading
#     data.append({"category": "<b>Purchase VAT</b>", "amount": None, "adjustment": None, "vat": None})

#     # Line 7 - Standard rated domestic purchases
#     data.append({
#         "category": "Standard rated domestic purchases",
#         "amount": purchase_totals["Standard"]["amount"],
#         "adjustment": purchase_totals["Standard"]["adjustment"],
#         "vat": purchase_totals["Standard"]["vat"]
#     })
#     # Line 8 - Imports subject to VAT paid at customs
#     data.append({
#     "category": "Imports subject to VAT paid at customs",
#     "amount": purchase_totals["ImportsCustoms"]["amount"],
#     "adjustment": purchase_totals["ImportsCustoms"]["adjustment"],
#     "vat": purchase_totals["ImportsCustoms"]["vat"],
#     })

#     # Line 9 - Imports subject to VAT accounted for through reverse charge mechanism
#     # data.append({
#     #     "category": "Imports subject to VAT accounted for through reverse charge mechanism",
#     #     "amount": 0, "adjustment": 0, "vat": 0
#     # })
#     # Line 10 - Zero rated purchases
#     data.append({
#         "category": "Zero rated purchases",
#         "amount": purchase_totals["Zero Rated"]["amount"],
#         "adjustment": purchase_totals["Zero Rated"]["adjustment"],
#         "vat": 0
#     })
#     # Line 11 - Exempt purchases
#     data.append({
#         "category": "Exempt purchases",
#         "amount": purchase_totals["Exempt"]["amount"],
#         "adjustment": purchase_totals["Exempt"]["adjustment"],
#         "vat": 0
#     })

#     # Line 12 - Total Purchases
#     data.append({
#         "category": "<b>Total purchases</b>",
#         "amount": sum(v["amount"] for v in purchase_totals.values()),
#         "adjustment": sum(v["adjustment"] for v in purchase_totals.values()),
#         "vat": sum(v["vat"] for v in purchase_totals.values()),
#     })

#     # # Line 13 - Total VAT due for current period (placeholder)
#     # data.append({
#     #     "category": "Total VAT due for current period",
#     #     "amount": 0, "adjustment": 0, "vat": 0
#     # })

#     # # Line 14 - Corrections from previous period
#     # data.append({
#     #     "category": "Corrections from previous period (between SAR ±5,000)",
#     #     "amount": 0, "adjustment": 0, "vat": 0
#     # })

#     # # Line 15 - VAT credit carried forward
#     # data.append({
#     #     "category": "VAT credit carried forward from previous period(s)",
#     #     "amount": 0, "adjustment": 0, "vat": 0
#     # })

#     # # Line 16 - Net VAT due (or claim)
#     # data.append({
#     #     "category": "<b>Net VAT due (or claim)</b>",
#     #     "amount": 0, "adjustment": 0, "vat": 0
#     # })

#     return columns, data

# def build_filters(filters):
#     """Construct frappe filters dict based on user input"""
#     if filters is None:
#         filters = {}

#     base_filters = {"docstatus": 1}

#     company = filters.get("company")
#     if company:
#         base_filters["company"] = company

#     from_date = filters.get("from_date")
#     to_date = filters.get("to_date")
#     if from_date and to_date:
#         base_filters["posting_date"] = ["between", [from_date, to_date]]
#     elif from_date:
#         base_filters["posting_date"] = [">=", from_date]
#     elif to_date:
#         base_filters["posting_date"] = ["<=", to_date]

#     return base_filters

# # -----------------------------
# # HELPERS
# # -----------------------------
# def get_sales_vat_totals(filters):
#     """Calculates totals for Sales VAT (with item tax template)"""
#     totals = {
#         "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
#         "HealthcareEdu": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Exports": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
#     }
#     base_filters  = build_filters(filters)
#     invoices = frappe.get_all(
#         "Sales Invoice",
#         filters=base_filters ,
#         fields=[
#             "name", "grand_total", "total_taxes_and_charges",
#             "custom_zatca_tax_category", "custom_zatca_export_invoice",
#             "custom_exemption_reason_code", "is_return"
#         ]
#     )

#     for inv in invoices:
#         doc = frappe.get_doc("Sales Invoice", inv.name)
#         is_return = 1 if doc.is_return else 0
#         has_item_template = any([item.item_tax_template for item in doc.items])

#         def calculate_item_vat(item):
#             if not item.item_tax_template:
#                 return 0
#             template = frappe.get_doc("Item Tax Template", item.item_tax_template)
#             if template.taxes:
#                 tax_rate = template.taxes[0].tax_rate or 0
#                 return item.net_amount * (tax_rate / 100)
#             return 0

#         key = "adjustment" if is_return else "amount"

#         # Standard Rated
#         if doc.custom_zatca_tax_category == "Standard":
#             totals["Standard"][key] += doc.grand_total
#             if not has_item_template:
#                 totals["Standard"]["vat"] += doc.total_taxes_and_charges
#         else:
#             for item in doc.items:
#                 if item.item_tax_template:
#                     template = frappe.get_doc("Item Tax Template", item.item_tax_template)
#                     if template.custom_zatca_tax_category == "Standard":
#                         totals["Standard"][key] += item.amount
#                         totals["Standard"]["vat"] += calculate_item_vat(item)

#         # Zero Rated
#         if doc.custom_zatca_tax_category == "Zero Rated":
#             totals["Zero Rated"][key] += doc.grand_total
#         else:
#             for item in doc.items:
#                 if item.item_tax_template:
#                     template = frappe.get_doc("Item Tax Template", item.item_tax_template)
#                     if template.custom_zatca_tax_category == "Zero Rated":
#                         totals["Zero Rated"][key] += item.amount

#         # Exports
#         if getattr(doc, "custom_zatca_export_invoice", 0) == 1:
#             totals["Exports"][key] += doc.grand_total
#             if not has_item_template:
#                 totals["Exports"]["vat"] += doc.total_taxes_and_charges

#         # Healthcare / Education
#         if doc.get("custom_exemption_reason_code") in ["VATEX-SA-HEA", "VATEX-SA-EDU"]:
#             totals["HealthcareEdu"][key] += doc.grand_total
#             if not has_item_template:
#                 totals["HealthcareEdu"]["vat"] += doc.total_taxes_and_charges
#         else:
#             for item in doc.items:
#                 if item.item_tax_template:
#                     template = frappe.get_doc("Item Tax Template", item.item_tax_template)
#                     if template.get("custom_exemption_reason_code") in ["VATEX-SA-HEA", "VATEX-SA-EDU"]:
#                         totals["HealthcareEdu"][key] += item.amount
#                         totals["HealthcareEdu"]["vat"] += calculate_item_vat(item)

#         # Exempt
#         if doc.custom_zatca_tax_category == "Exempted":
#             totals["Exempt"][key] += doc.grand_total
#         else:
#             for item in doc.items:
#                 if item.item_tax_template:
#                     template = frappe.get_doc("Item Tax Template", item.item_tax_template)
#                     if template.custom_zatca_tax_category == "Exempted":
#                         totals["Exempt"][key] += item.amount

#     return totals


# def get_purchase_vat_totals(filters):
#     """Calculates totals for Purchase VAT using only common fields (no item tax template)"""
#     totals = {
#         "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
#         "HealthcareEdu": {"amount": 0, "adjustment": 0, "vat": 0},
#         "ImportsCustoms": {"amount": 0, "adjustment": 0, "vat": 0},    # Not used in VAT form but kept for completeness
#         "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
#     }
#     base_filters  = build_filters(filters)
#     purchases = frappe.get_all(
#         "Purchase Invoice",
#         filters=base_filters,
#         fields=[
#             "name", "grand_total", "total_taxes_and_charges",
#             "custom_zatca_tax_category", "custom_exemption_reason_code",
#             "custom_zatca_import_invoice", "is_return"
#         ]
#     )

#     for inv in purchases:
#         doc = frappe.get_doc("Purchase Invoice", inv.name)
#         is_return = 1 if doc.is_return else 0
#         key = "adjustment" if is_return else "amount"

#         # Standard
#         if doc.custom_zatca_tax_category == "Standard":
#             totals["Standard"][key] += doc.grand_total
#             totals["Standard"]["vat"] += doc.total_taxes_and_charges

#         # Zero Rated
#         elif doc.custom_zatca_tax_category == "Zero Rated":
#             totals["Zero Rated"][key] += doc.grand_total

#         # Healthcare / Education
#         # elif doc.get("custom_exemption_reason_code") in ["VATEX-SA-HEA", "VATEX-SA-EDU"]:
#         #     totals["HealthcareEdu"][key] += doc.grand_total
#         #     totals["HealthcareEdu"]["vat"] += doc.total_taxes_and_charges

#         # Exempt
#         elif doc.custom_zatca_tax_category == "Exempted":
#             totals["Exempt"][key] += doc.grand_total
        
#         if getattr(doc, "custom_zatca_import_invoice", 0) == 1:
#             # Imports subject to VAT paid at customs
#             totals["ImportsCustoms"][key] += doc.grand_total
#             totals["ImportsCustoms"]["vat"] += doc.total_taxes_and_charges


#     return totals


# def get_columns():
#     return [
#         {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 380, "options": "HTML"},
#         {"label": "Amount (SAR)", "fieldname": "amount", "fieldtype": "Currency", "width": 180},
#         {"label": "Adjustment (SAR)", "fieldname": "adjustment", "fieldtype": "Currency", "width": 180},
#         {"label": "VAT Amount (SAR)", "fieldname": "vat", "fieldtype": "Currency", "width": 180},
#     ]


import frappe

def execute(filters=None):
    columns, data = get_columns(), []

    # -----------------------------
    # 1. SALES VAT
    # -----------------------------
    sales_totals = get_sales_vat_totals(filters)

    # Sales VAT heading
    data.append({"category": "<b>Sales VAT</b>", "amount": None, "adjustment": None, "vat": None})

    # Sales lines
    data.append({
        "category": "Standard rated sales",
        "amount": sales_totals["Standard"]["amount"],
        "adjustment": sales_totals["Standard"]["adjustment"],
        "vat": sales_totals["Standard"]["vat"]
    })
    data.append({
        "category": "Private Healthcare / Private Education sales to citizens",
        "amount": sales_totals["HealthcareEdu"]["amount"],
        "adjustment": sales_totals["HealthcareEdu"]["adjustment"],
        "vat": sales_totals["HealthcareEdu"]["vat"]
    })
    data.append({
        "category": "Zero rated domestic sales",
        "amount": sales_totals["Zero Rated"]["amount"],
        "adjustment": sales_totals["Zero Rated"]["adjustment"],
        "vat": 0
    })
    data.append({
        "category": "Exports",
        "amount": sales_totals["Exports"]["amount"],
        "adjustment": sales_totals["Exports"]["adjustment"],
        "vat": sales_totals["Exports"]["vat"]
    })
    data.append({
        "category": "Exempt sales",
        "amount": sales_totals["Exempt"]["amount"],
        "adjustment": sales_totals["Exempt"]["adjustment"],
        "vat": 0
    })

    # Total Sales line
    data.append({
        "category": "<b>Total Sales</b>",
        "amount": sum(v["amount"] for v in sales_totals.values()),
        "adjustment": sum(v["adjustment"] for v in sales_totals.values()),
        "vat": sum(v["vat"] for v in sales_totals.values()),
    })

    # -----------------------------
    # 2. PURCHASE VAT
    # -----------------------------
    purchase_totals = get_purchase_vat_totals(filters)

    # Empty row for spacing
    data.append({"category": "", "amount": None, "adjustment": None, "vat": None})

    # Purchase VAT heading
    data.append({"category": "<b>Purchase VAT</b>", "amount": None, "adjustment": None, "vat": None})

    # Line 7 - Standard rated domestic purchases
    data.append({
        "category": "Standard rated domestic purchases",
        "amount": purchase_totals["Standard"]["amount"],
        "adjustment": purchase_totals["Standard"]["adjustment"],
        "vat": purchase_totals["Standard"]["vat"]
    })

    # Line 8 - Imports subject to VAT paid at customs
    data.append({
        "category": "Imports subject to VAT paid at customs",
        "amount": purchase_totals["ImportsCustoms"]["amount"],
        "adjustment": purchase_totals["ImportsCustoms"]["adjustment"],
        "vat": purchase_totals["ImportsCustoms"]["vat"],
    })

    # Line 10 - Zero rated purchases
    data.append({
        "category": "Zero rated purchases",
        "amount": purchase_totals["Zero Rated"]["amount"],
        "adjustment": purchase_totals["Zero Rated"]["adjustment"],
        "vat": 0
    })

    # Line 11 - Exempt purchases
    data.append({
        "category": "Exempt purchases",
        "amount": purchase_totals["Exempt"]["amount"],
        "adjustment": purchase_totals["Exempt"]["adjustment"],
        "vat": 0
    })

    # Line 12 - Total Purchases
    data.append({
        "category": "<b>Total purchases</b>",
        "amount": sum(v["amount"] for v in purchase_totals.values()),
        "adjustment": sum(v["adjustment"] for v in purchase_totals.values()),
        "vat": sum(v["vat"] for v in purchase_totals.values()),
    })

    return columns, data


# -----------------------------
# FILTER BUILDER
# -----------------------------
def build_filters(filters):
    if filters is None:
        filters = {}

    base_filters = {"docstatus": 1}

    if filters.get("company"):
        base_filters["company"] = filters["company"]

    if filters.get("from_date") and filters.get("to_date"):
        base_filters["posting_date"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        base_filters["posting_date"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        base_filters["posting_date"] = ["<=", filters["to_date"]]

    return base_filters


# -----------------------------
# SALES TOTALS
# -----------------------------
def get_sales_vat_totals(filters):
    totals = {
        "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
        "HealthcareEdu": {"amount": 0, "adjustment": 0, "vat": 0},
        "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
        "Exports": {"amount": 0, "adjustment": 0, "vat": 0},
        "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
    }

    base_filters = build_filters(filters)
    invoices = frappe.get_all(
        "Sales Invoice",
        filters=base_filters,
        fields=["name", "grand_total", "total_taxes_and_charges",
                "custom_zatca_tax_category", "custom_zatca_export_invoice",
                "custom_exemption_reason_code", "is_return"]
    )

    # Fetch all items in one go
    items = frappe.get_all(
        "Sales Invoice Item",
        filters={"parent": ["in", [inv.name for inv in invoices]]},
        fields=["parent", "amount", "net_amount", "item_tax_template"]
    )

    # Cache tax templates
    template_cache = {}
    def get_template(template_name):
        if template_name not in template_cache:
            template_cache[template_name] = frappe.get_value(
                "Item Tax Template", template_name,
                ["custom_zatca_tax_category", "custom_exemption_reason_code", "taxes"], as_dict=True
            )
        return template_cache[template_name]

    items_by_invoice = {}
    for item in items:
        items_by_invoice.setdefault(item.parent, []).append(item)

    for inv in invoices:
        key = "adjustment" if inv.is_return else "amount"
        inv_items = items_by_invoice.get(inv.name, [])

        has_item_template = any(it.item_tax_template for it in inv_items)

        def calculate_item_vat(it):
            if not it.item_tax_template:
                return 0
            template = get_template(it.item_tax_template)
            if template and template.get("taxes"):
                # template.taxes is JSON in db, so safer is fetch from Doc if needed
                tax_doc = frappe.get_doc("Item Tax Template", it.item_tax_template)
                if tax_doc.taxes:
                    tax_rate = tax_doc.taxes[0].tax_rate or 0
                    return it.net_amount * (tax_rate / 100)
            return 0

        # Standard Rated
        if inv.custom_zatca_tax_category == "Standard":
            totals["Standard"][key] += inv.grand_total
            if not has_item_template:
                totals["Standard"]["vat"] += inv.total_taxes_and_charges
        else:
            for it in inv_items:
                if it.item_tax_template:
                    template = get_template(it.item_tax_template)
                    if template and template.get("custom_zatca_tax_category") == "Standard":
                        totals["Standard"][key] += it.amount
                        totals["Standard"]["vat"] += calculate_item_vat(it)

        # Zero Rated
        if inv.custom_zatca_tax_category == "Zero Rated":
            totals["Zero Rated"][key] += inv.grand_total
        else:
            for it in inv_items:
                if it.item_tax_template:
                    template = get_template(it.item_tax_template)
                    if template and template.get("custom_zatca_tax_category") == "Zero Rated":
                        totals["Zero Rated"][key] += it.amount

        # Exports
        if getattr(inv, "custom_zatca_export_invoice", 0) == 1:
            totals["Exports"][key] += inv.grand_total
            if not has_item_template:
                totals["Exports"]["vat"] += inv.total_taxes_and_charges

        # Healthcare/Education
        if inv.custom_exemption_reason_code in ["VATEX-SA-HEA", "VATEX-SA-EDU"]:
            totals["HealthcareEdu"][key] += inv.grand_total
            if not has_item_template:
                totals["HealthcareEdu"]["vat"] += inv.total_taxes_and_charges
        else:
            for it in inv_items:
                if it.item_tax_template:
                    template = get_template(it.item_tax_template)
                    if template and template.get("custom_exemption_reason_code") in ["VATEX-SA-HEA", "VATEX-SA-EDU"]:
                        totals["HealthcareEdu"][key] += it.amount
                        totals["HealthcareEdu"]["vat"] += calculate_item_vat(it)

        # Exempt
        if inv.custom_zatca_tax_category == "Exempted":
            totals["Exempt"][key] += inv.grand_total
        else:
            for it in inv_items:
                if it.item_tax_template:
                    template = get_template(it.item_tax_template)
                    if template and template.get("custom_zatca_tax_category") == "Exempted":
                        totals["Exempt"][key] += it.amount

    return totals


# -----------------------------
# PURCHASE TOTALS
# -----------------------------
def get_purchase_vat_totals(filters):
    totals = {
        "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
        "HealthcareEdu": {"amount": 0, "adjustment": 0, "vat": 0},
        "ImportsCustoms": {"amount": 0, "adjustment": 0, "vat": 0},
        "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
        "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
    }

    base_filters = build_filters(filters)
    purchases = frappe.get_all(
        "Purchase Invoice",
        filters=base_filters,
        fields=["name", "grand_total", "total_taxes_and_charges",
                "custom_zatca_tax_category", "custom_exemption_reason_code",
                "custom_zatca_import_invoice", "is_return"]
    )

    for inv in purchases:
        key = "adjustment" if inv.is_return else "amount"

        if inv.custom_zatca_tax_category == "Standard":
            totals["Standard"][key] += inv.grand_total
            totals["Standard"]["vat"] += inv.total_taxes_and_charges

        elif inv.custom_zatca_tax_category == "Zero Rated":
            totals["Zero Rated"][key] += inv.grand_total

        elif inv.custom_zatca_tax_category == "Exempted":
            totals["Exempt"][key] += inv.grand_total

        if getattr(inv, "custom_zatca_import_invoice", 0) == 1:
            totals["ImportsCustoms"][key] += inv.grand_total
            totals["ImportsCustoms"]["vat"] += inv.total_taxes_and_charges

    return totals


# -----------------------------
# COLUMNS
# -----------------------------
def get_columns():
    return [
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 380, "options": "HTML"},
        {"label": "Amount (SAR)", "fieldname": "amount", "fieldtype": "Currency", "width": 180},
        {"label": "Adjustment (SAR)", "fieldname": "adjustment", "fieldtype": "Currency", "width": 180},
        {"label": "VAT Amount (SAR)", "fieldname": "vat", "fieldtype": "Currency", "width": 180},
    ]
