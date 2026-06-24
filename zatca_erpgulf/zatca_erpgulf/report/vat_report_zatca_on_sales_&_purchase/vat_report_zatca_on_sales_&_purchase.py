

import frappe
from frappe import _
from frappe.utils import cint

def execute(filters=None):
    columns = get_columns()
    data = []

    # =========================================================
    # SALES VAT
    # =========================================================
    sales_totals = get_sales_vat_totals_sql(filters)
    other_income = get_other_income_tax(filters)

    data.append({
        "category": "<b>Sales VAT</b>",
        "amount": None,
        "adjustment": None,
        "vat": None
    })

    data += [
        {
            "category": "Standard rated sales",
            "amount": sales_totals["Standard"]["amount"],
            "adjustment": sales_totals["Standard"]["adjustment"],
            "vat": sales_totals["Standard"]["vat"],
        },
        {
            "category": "Private Healthcare / Private Education sales to citizens",
            "amount": sales_totals["HealthcareEdu"]["amount"],
            "adjustment": sales_totals["HealthcareEdu"]["adjustment"],
            "vat": sales_totals["HealthcareEdu"]["vat"],
        },
        {
            "category": "Zero rated domestic sales",
            "amount": sales_totals["Zero Rated"]["amount"],
            "adjustment": sales_totals["Zero Rated"]["adjustment"],
            "vat": 0,
        },
        {
            "category": "Exports",
            "amount": sales_totals["Exports"]["amount"],
            "adjustment": sales_totals["Exports"]["adjustment"],
            "vat": sales_totals["Exports"]["vat"],
        },
        {
            "category": "Exempt sales",
            "amount": sales_totals["Exempt"]["amount"],
            "adjustment": sales_totals["Exempt"]["adjustment"],
            "vat": 0,
        },
        # ---- NEW ROW ----
        {
            "category": "Tax on other income",
            "amount": other_income["amount"],
            "adjustment": other_income["adjustment"],
            "vat": other_income["vat"],
        },
        {
            "category": "<b>Total Sales</b>",
            "amount": sum(v["amount"] for v in sales_totals.values()),
            "adjustment": sum(v["adjustment"] for v in sales_totals.values()),
            "vat": sum(v["vat"] for v in sales_totals.values()) + (other_income["vat"] or 0),
        },
    ]

    total_sales_vat = sum(v["vat"] for v in sales_totals.values()) + (other_income["vat"] or 0)

    # =========================================================
    # PURCHASE VAT
    # =========================================================
    purchase_totals = get_purchase_vat_totals_sql(filters)
    other_expense = get_other_expense_tax(filters)

    data.append({
        "category": "",
        "amount": None,
        "adjustment": None,
        "vat": None
    })

    data.append({
        "category": "<b>Purchase VAT</b>",
        "amount": None,
        "adjustment": None,
        "vat": None
    })

    data += [
        {
            "category": "Standard rated domestic purchases",
            "amount": purchase_totals["Standard"]["amount"],
            "adjustment": purchase_totals["Standard"]["adjustment"],
            "vat": purchase_totals["Standard"]["vat"],
        },
        {
            "category": "Imports subject to VAT paid at customs",
            "amount": purchase_totals["ImportsCustoms"]["amount"],
            "adjustment": purchase_totals["ImportsCustoms"]["adjustment"],
            "vat": purchase_totals["ImportsCustoms"]["vat"],
        },
        {
            "category": "Zero rated purchases",
            "amount": purchase_totals["Zero Rated"]["amount"],
            "adjustment": purchase_totals["Zero Rated"]["adjustment"],
            "vat": 0,
        },
        {
            "category": "Exempt purchases",
            "amount": purchase_totals["Exempt"]["amount"],
            "adjustment": purchase_totals["Exempt"]["adjustment"],
            "vat": 0,
        },
        # ---- NEW ROW ----
        {
            "category": "Tax on other expenses",
            "amount": other_expense["amount"],
            "adjustment": other_expense["adjustment"],
            "vat": other_expense["vat"],
        },
        {
            "category": "<b>Total purchases</b>",
            "amount": sum(v["amount"] for v in purchase_totals.values()),
            "adjustment": sum(v["adjustment"] for v in purchase_totals.values()),
            "vat": sum(v["vat"] for v in purchase_totals.values()) + (other_expense["vat"] or 0),
        },
    ]

    total_purchase_vat = sum(v["vat"] for v in purchase_totals.values()) + (other_expense["vat"] or 0)

    vat_difference = total_sales_vat - total_purchase_vat

    data.append({
        "category": "<b>Net VAT Due (or Claim = Sales VAT - Purchases VAT)</b>",
        "amount": None,
        "adjustment": None,
        "vat": vat_difference,
    })

    return columns, data


# =========================================================
# COMMON FILTERS
# =========================================================
def build_filters_sql(filters, table_alias="si"):
    conditions = [f"{table_alias}.docstatus = 1"]

    if filters:
        if filters.get("company"):
            conditions.append(f"{table_alias}.company = %(company)s")

        if filters.get("from_date") and filters.get("to_date"):
            conditions.append(
                f"{table_alias}.posting_date BETWEEN %(from_date)s AND %(to_date)s"
            )

        elif filters.get("from_date"):
            conditions.append(
                f"{table_alias}.posting_date >= %(from_date)s"
            )

        elif filters.get("to_date"):
            conditions.append(
                f"{table_alias}.posting_date <= %(to_date)s"
            )

    return " AND ".join(conditions)


# # =========================================================
# # SALES VAT
# # =========================================================
# def get_sales_vat_totals_sql(filters):

#     totals = {
#         "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
#         "HealthcareEdu": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Exports": {"amount": 0, "adjustment": 0, "vat": 0},
#         "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
#     }

#     where_clause = build_filters_sql(filters)

#     query = f"""
#         SELECT
#             si.name AS invoice,
#             si.is_return AS is_return,
#             si.is_debit_note,
#             si.grand_total AS grand_total,

#             COALESCE((
#                 SELECT SUM(stc.tax_amount)
#                 FROM `tabSales Taxes and Charges` stc
#                 INNER JOIN `tabAccount` acc
#                     ON acc.name = stc.account_head
#                 WHERE stc.parent = si.name
#                 AND acc.account_type = 'Tax'
#             ), 0) AS total_vat_amount,

#             si.custom_zatca_tax_category AS invoice_zatca_cat,
#             si.custom_exemption_reason_code AS invoice_exemption_code,
#             si.custom_zatca_export_invoice AS invoice_export_flag,

#             sii.name AS item_name,
#             COALESCE(sii.amount, 0) AS item_amount,
#             COALESCE(sii.net_amount, sii.amount, 0) AS item_net_amount,
#             sii.item_tax_template AS item_tax_template,

#             itt.custom_zatca_tax_category AS template_category,
#             itt.custom_exemption_reason_code AS template_exemption_code,

#             tax.tax_rate AS template_first_tax_rate

#         FROM `tabSales Invoice` si

#         LEFT JOIN `tabSales Invoice Item` sii
#             ON sii.parent = si.name

#         LEFT JOIN `tabItem Tax Template` itt
#             ON itt.name = sii.item_tax_template

#         LEFT JOIN `tabItem Tax Template Detail` tax
#             ON tax.parent = itt.name
#             AND tax.idx = 1

#         WHERE {where_clause}
#     """

#     rows = frappe.db.sql(query, filters, as_dict=True)

#     invoices = {}

#     for r in rows:

#         inv = r.get("invoice")

#         if inv not in invoices:
#             invoices[inv] = {
#                 "is_return": bool(r.get("is_return")),
#                 "is_debit_note": bool(r.get("is_debit_note")),
#                 "grand_total": r.get("grand_total") or 0,
#                 "total_vat_amount": r.get("total_vat_amount") or 0,
#                 "custom_zatca_tax_category": r.get("invoice_zatca_cat"),
#                 "custom_exemption_reason_code": r.get("invoice_exemption_code"),
#                 "custom_zatca_export_invoice": r.get("invoice_export_flag") or 0,
#                 "items": []
#             }

#         if r.get("item_name"):
#             invoices[inv]["items"].append({
#                 "amount": r.get("item_amount") or 0,
#                 "net_amount": r.get("item_net_amount") or 0,
#                 "item_tax_template": r.get("item_tax_template"),
#                 "template_category": r.get("template_category"),
#                 "template_exemption_code": r.get("template_exemption_code"),
#                 "tax_rate": r.get("template_first_tax_rate") or 0,
#             })

#     for inv_doc in invoices.values():

#         is_return = bool(inv_doc["is_return"])
#         is_debit = bool(inv_doc["is_debit_note"])

#         key = "adjustment" if (is_return or is_debit) else "amount"

#         has_item_template = any(
#             item.get("item_tax_template")
#             for item in inv_doc["items"]
#         )

#         def calculate_item_vat(item):
#             return (
#                 (item.get("net_amount") or 0)
#                 * (item.get("tax_rate") or 0)
#                 / 100.0
#             )

#         signed_grand_total = inv_doc["grand_total"] or 0
#         signed_vat = inv_doc["total_vat_amount"] or 0

#         if is_return:
#             signed_grand_total = -abs(signed_grand_total)
#             signed_vat = -abs(signed_vat)

#         elif is_debit:
#             signed_grand_total = abs(signed_grand_total)
#             signed_vat = abs(signed_vat)

#         # STANDARD
#         if inv_doc.get("custom_zatca_tax_category") == "Standard":

#             totals["Standard"][key] += signed_grand_total

#             if not has_item_template:
#                 totals["Standard"]["vat"] += signed_vat

#         else:

#             for item in inv_doc["items"]:

#                 if item.get("template_category") == "Standard":

#                     item_amount = item.get("amount") or 0
#                     item_vat = calculate_item_vat(item)

#                     if is_return:
#                         item_amount = -abs(item_amount)
#                         item_vat = -abs(item_vat)

#                     elif is_debit:
#                         item_amount = abs(item_amount)
#                         item_vat = abs(item_vat)

#                     totals["Standard"][key] += item_amount
#                     totals["Standard"]["vat"] += item_vat

#         # ZERO RATED
#         if inv_doc.get("custom_zatca_tax_category") == "Zero Rated":

#             totals["Zero Rated"][key] += signed_grand_total

#         else:

#             for item in inv_doc["items"]:

#                 if item.get("template_category") == "Zero Rated":

#                     item_amount = item.get("amount") or 0

#                     if is_return:
#                         item_amount = -abs(item_amount)

#                     elif is_debit:
#                         item_amount = abs(item_amount)

#                     totals["Zero Rated"][key] += item_amount

#         # EXPORTS
#         if int(inv_doc.get("custom_zatca_export_invoice") or 0) == 1:

#             totals["Exports"][key] += signed_grand_total

#             if not has_item_template:
#                 totals["Exports"]["vat"] += signed_vat

#         # HEALTHCARE / EDUCATION
#         if inv_doc.get("custom_exemption_reason_code") in [
#             "VATEX-SA-HEA",
#             "VATEX-SA-EDU"
#         ]:

#             totals["HealthcareEdu"][key] += signed_grand_total

#             if not has_item_template:
#                 totals["HealthcareEdu"]["vat"] += signed_vat

#         else:

#             for item in inv_doc["items"]:

#                 if item.get("template_exemption_code") in [
#                     "VATEX-SA-HEA",
#                     "VATEX-SA-EDU"
#                 ]:

#                     item_amount = item.get("amount") or 0
#                     item_vat = calculate_item_vat(item)

#                     if is_return:
#                         item_amount = -abs(item_amount)
#                         item_vat = -abs(item_vat)

#                     elif is_debit:
#                         item_amount = abs(item_amount)
#                         item_vat = abs(item_vat)

#                     totals["HealthcareEdu"][key] += item_amount
#                     totals["HealthcareEdu"]["vat"] += item_vat

#         # EXEMPT
#         if inv_doc.get("custom_zatca_tax_category") == "Exempted":

#             totals["Exempt"][key] += signed_grand_total

#         else:

#             for item in inv_doc["items"]:

#                 if item.get("template_category") == "Exempted":

#                     item_amount = item.get("amount") or 0

#                     if is_return:
#                         item_amount = -abs(item_amount)

#                     elif is_debit:
#                         item_amount = abs(item_amount)

#                     totals["Exempt"][key] += item_amount

#     return totals

# =========================================================
# SALES VAT - FIXED VERSION
# =========================================================
def get_sales_vat_totals_sql(filters):

    totals = {
        "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
        "HealthcareEdu": {"amount": 0, "adjustment": 0, "vat": 0},
        "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
        "Exports": {"amount": 0, "adjustment": 0, "vat": 0},
        "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
    }

    where_clause = build_filters_sql(filters)

    query = f"""
        SELECT
            si.name AS invoice,
            si.is_return AS is_return,
            si.is_debit_note,
            si.grand_total AS grand_total,

            COALESCE((
                SELECT SUM(stc.tax_amount)
                FROM `tabSales Taxes and Charges` stc
                INNER JOIN `tabAccount` acc
                    ON acc.name = stc.account_head
                WHERE stc.parent = si.name
                AND acc.account_type = 'Tax'
            ), 0) AS total_vat_amount,

            si.custom_zatca_tax_category AS invoice_zatca_cat,
            si.custom_exemption_reason_code AS invoice_exemption_code,
            si.custom_zatca_export_invoice AS invoice_export_flag,

            sii.name AS item_name,
            COALESCE(sii.amount, 0) AS item_amount,
            COALESCE(sii.net_amount, sii.amount, 0) AS item_net_amount,
            sii.item_tax_template AS item_tax_template,

            itt.custom_zatca_tax_category AS template_category,
            itt.custom_exemption_reason_code AS template_exemption_code,

            tax.tax_rate AS template_first_tax_rate

        FROM `tabSales Invoice` si

        LEFT JOIN `tabSales Invoice Item` sii
            ON sii.parent = si.name

        LEFT JOIN `tabItem Tax Template` itt
            ON itt.name = sii.item_tax_template

        LEFT JOIN `tabItem Tax Template Detail` tax
            ON tax.parent = itt.name
            AND tax.idx = 1

        WHERE {where_clause}
    """

    rows = frappe.db.sql(query, filters, as_dict=True)

    invoices = {}

    for r in rows:

        inv = r.get("invoice")

        if inv not in invoices:
            invoices[inv] = {
                "is_return": bool(r.get("is_return")),
                "is_debit_note": bool(r.get("is_debit_note")),
                "grand_total": r.get("grand_total") or 0,
                "total_vat_amount": r.get("total_vat_amount") or 0,
                "custom_zatca_tax_category": r.get("invoice_zatca_cat"),
                "custom_exemption_reason_code": r.get("invoice_exemption_code"),
                "custom_zatca_export_invoice": r.get("invoice_export_flag") or 0,
                "items": []
            }

        if r.get("item_name"):
            invoices[inv]["items"].append({
                "amount": r.get("item_amount") or 0,
                "net_amount": r.get("item_net_amount") or 0,
                "item_tax_template": r.get("item_tax_template"),
                "template_category": r.get("template_category"),
                "template_exemption_code": r.get("template_exemption_code"),
                "tax_rate": r.get("template_first_tax_rate") or 0,
            })

    for inv_doc in invoices.values():

        is_return = bool(inv_doc["is_return"])
        is_debit = bool(inv_doc["is_debit_note"])

        key = "adjustment" if (is_return or is_debit) else "amount"

        def calculate_item_vat(item):
            return (
                (item.get("net_amount") or 0)
                * (item.get("tax_rate") or 0)
                / 100.0
            )

        signed_grand_total = inv_doc["grand_total"] or 0
        signed_vat = inv_doc["total_vat_amount"] or 0

        if is_return:
            signed_grand_total = -abs(signed_grand_total)
            signed_vat = -abs(signed_vat)

        elif is_debit:
            signed_grand_total = abs(signed_grand_total)
            signed_vat = abs(signed_vat)

        # STANDARD - Always use actual VAT from database
        if inv_doc.get("custom_zatca_tax_category") == "Standard":

            totals["Standard"][key] += signed_grand_total
            totals["Standard"]["vat"] += signed_vat

        else:

            for item in inv_doc["items"]:

                if item.get("template_category") == "Standard":

                    item_amount = item.get("amount") or 0
                    item_vat = calculate_item_vat(item)

                    if is_return:
                        item_amount = -abs(item_amount)
                        item_vat = -abs(item_vat)

                    elif is_debit:
                        item_amount = abs(item_amount)
                        item_vat = abs(item_vat)

                    totals["Standard"][key] += item_amount
                    totals["Standard"]["vat"] += item_vat

        # ZERO RATED
        if inv_doc.get("custom_zatca_tax_category") == "Zero Rated":

            totals["Zero Rated"][key] += signed_grand_total

        else:

            for item in inv_doc["items"]:

                if item.get("template_category") == "Zero Rated":

                    item_amount = item.get("amount") or 0

                    if is_return:
                        item_amount = -abs(item_amount)

                    elif is_debit:
                        item_amount = abs(item_amount)

                    totals["Zero Rated"][key] += item_amount

        # EXPORTS - Always use actual VAT from database
        if int(inv_doc.get("custom_zatca_export_invoice") or 0) == 1:

            totals["Exports"][key] += signed_grand_total
            totals["Exports"]["vat"] += signed_vat

        # HEALTHCARE / EDUCATION - Always use actual VAT from database
        if inv_doc.get("custom_exemption_reason_code") in [
            "VATEX-SA-HEA",
            "VATEX-SA-EDU"
        ]:

            totals["HealthcareEdu"][key] += signed_grand_total
            totals["HealthcareEdu"]["vat"] += signed_vat

        else:

            for item in inv_doc["items"]:

                if item.get("template_exemption_code") in [
                    "VATEX-SA-HEA",
                    "VATEX-SA-EDU"
                ]:

                    item_amount = item.get("amount") or 0
                    item_vat = calculate_item_vat(item)

                    if is_return:
                        item_amount = -abs(item_amount)
                        item_vat = -abs(item_vat)

                    elif is_debit:
                        item_amount = abs(item_amount)
                        item_vat = abs(item_vat)

                    totals["HealthcareEdu"][key] += item_amount
                    totals["HealthcareEdu"]["vat"] += item_vat

        # EXEMPT
        if inv_doc.get("custom_zatca_tax_category") == "Exempted":

            totals["Exempt"][key] += signed_grand_total

        else:

            for item in inv_doc["items"]:

                if item.get("template_category") == "Exempted":

                    item_amount = item.get("amount") or 0

                    if is_return:
                        item_amount = -abs(item_amount)

                    elif is_debit:
                        item_amount = abs(item_amount)

                    totals["Exempt"][key] += item_amount

    return totals
# =========================================================
# PURCHASE VAT
# =========================================================
def get_purchase_vat_totals_sql(filters):

    totals = {
        "Standard": {"amount": 0, "adjustment": 0, "vat": 0},
        "ImportsCustoms": {"amount": 0, "adjustment": 0, "vat": 0},
        "Zero Rated": {"amount": 0, "adjustment": 0, "vat": 0},
        "Exempt": {"amount": 0, "adjustment": 0, "vat": 0},
    }

    where_clause = build_filters_sql(filters, table_alias="pi")

    query = f"""
        SELECT
            pi.name AS invoice,
            pi.is_return AS is_return,
            pi.base_grand_total AS grand_total,

            COALESCE((
                SELECT SUM(ptc.base_tax_amount)
                FROM `tabPurchase Taxes and Charges` ptc
                INNER JOIN `tabAccount` acc
                    ON acc.name = ptc.account_head
                WHERE ptc.parent = pi.name
                AND acc.account_type = 'Tax'
            ), 0) AS total_vat_amount,

            COALESCE((
                SELECT SUM(ptc.base_tax_amount)
                FROM `tabPurchase Taxes and Charges` ptc
                INNER JOIN `tabAccount` acc
                    ON acc.name = ptc.account_head
                WHERE ptc.parent = pi.name
                AND acc.account_type != 'Tax'
            ), 0) AS total_customs_amount,

            pi.custom_zatca_tax_category,
            pi.custom_exemption_reason_code,
            pi.custom_zatca_import_invoice

        FROM `tabPurchase Invoice` pi

        WHERE {where_clause}
    """

    rows = frappe.db.sql(query, filters, as_dict=True)

    for r in rows:

        is_return = bool(r.get("is_return"))

        key = "adjustment" if is_return else "amount"

        signed_grand_total = r.get("grand_total") or 0
        signed_vat = r.get("total_vat_amount") or 0
        signed_customs_vat = r.get("total_customs_amount") or 0

        if is_return:
            signed_grand_total = -abs(signed_grand_total)
            signed_vat = -abs(signed_vat)
            signed_customs_vat = -abs(signed_customs_vat)

        # IMPORTS ONLY
        if cint(r.get("custom_zatca_import_invoice")) == 1:
            totals["ImportsCustoms"][key] += signed_grand_total
            totals["ImportsCustoms"]["vat"] += signed_customs_vat

        # STANDARD ONLY (NON-IMPORTS)
        elif r.get("custom_zatca_tax_category") == "Standard":
            totals["Standard"][key] += signed_grand_total
            totals["Standard"]["vat"] += signed_vat

        # ZERO RATED ONLY (NON-IMPORTS)
        elif r.get("custom_zatca_tax_category") == "Zero Rated":
            totals["Zero Rated"][key] += signed_grand_total

        # EXEMPT ONLY (NON-IMPORTS)
        elif r.get("custom_zatca_tax_category") == "Exempted":
            totals["Exempt"][key] += signed_grand_total

    return totals
# =========================================================
# OTHER INCOME TAX
# Picks up GL Entries where:
#   - account_type = 'Tax'
#   - custom_zatca_account_type is NOT blank (any value: Input Tax, Output Tax, Both)
#   - voucher_type is NOT Sales Invoice or Purchase Invoice
#   - same company + date filters as the report
# VAT = SUM(credit - debit)  →  income/output tax is a credit
# =========================================================
def get_other_income_tax(filters):

    conditions = ["gle.docstatus = 1"]

    if filters:

        if filters.get("company"):
            conditions.append("gle.company = %(company)s")

        if filters.get("from_date") and filters.get("to_date"):
            conditions.append(
                "gle.posting_date BETWEEN %(from_date)s AND %(to_date)s"
            )
        elif filters.get("from_date"):
            conditions.append("gle.posting_date >= %(from_date)s")
        elif filters.get("to_date"):
            conditions.append("gle.posting_date <= %(to_date)s")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN IFNULL(acc.custom_zatca_account_type, '') = 'Output Tax'
                    THEN (gle.debit - gle.credit)
                    ELSE 0
                END
            ), 0)
            +
            COALESCE(SUM(
                CASE
                    WHEN IFNULL(acc.custom_zatca_account_type, '') = 'Both'
                    THEN gle.credit
                    ELSE 0
                END
            ), 0) AS vat_amount

        FROM `tabGL Entry` gle

        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account

        WHERE {where_clause}
            AND acc.account_type = 'Tax'
            AND IFNULL(acc.custom_zatca_account_type, '') IN ('Output Tax', 'Both')
            AND gle.voucher_type NOT IN ('Sales Invoice', 'Purchase Invoice')
            AND gle.is_cancelled = 0
    """

    result = frappe.db.sql(query, filters, as_dict=True)

    vat_amount = (
        result[0].get("vat_amount")
        if result and result[0].get("vat_amount")
        else 0
    )

    return {
        "amount": None,
        "adjustment": None,
        "vat": vat_amount
    }


# =========================================================
# OTHER EXPENSE TAX
# Same logic but VAT = SUM(debit - credit)  →  expense/input tax is a debit
# =========================================================
def get_other_expense_tax(filters):

    conditions = ["gle.docstatus = 1"]

    if filters:

        if filters.get("company"):
            conditions.append("gle.company = %(company)s")

        if filters.get("from_date") and filters.get("to_date"):
            conditions.append(
                "gle.posting_date BETWEEN %(from_date)s AND %(to_date)s"
            )
        elif filters.get("from_date"):
            conditions.append("gle.posting_date >= %(from_date)s")
        elif filters.get("to_date"):
            conditions.append("gle.posting_date <= %(to_date)s")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN IFNULL(acc.custom_zatca_account_type, '') = 'Input Tax'
                    THEN (gle.debit - gle.credit)
                    ELSE 0
                END
            ), 0)
            +
            COALESCE(SUM(
                CASE
                    WHEN IFNULL(acc.custom_zatca_account_type, '') = 'Both'
                    THEN gle.debit
                    ELSE 0
                END
            ), 0) AS vat_amount

        FROM `tabGL Entry` gle

        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account

        WHERE {where_clause}
            AND acc.account_type = 'Tax'
            AND IFNULL(acc.custom_zatca_account_type, '') IN ('Input Tax', 'Both')
            AND gle.voucher_type NOT IN ('Sales Invoice', 'Purchase Invoice')
            AND gle.is_cancelled = 0
    """

    result = frappe.db.sql(query, filters, as_dict=True)

    vat_amount = (
        result[0].get("vat_amount")
        if result and result[0].get("vat_amount")
        else 0
    )

    return {
        "amount": None,
        "adjustment": None,
        "vat": vat_amount
    }


# =========================================================
# COLUMNS
# =========================================================
def get_columns():
    return [
        {
            "label": _("Category"),
            "fieldname": "category",
            "fieldtype": "Data",
            "width": 380,
            "options": "HTML"
        },
        {
            "label": _("Amount (SAR)"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 180
        },
        {
            "label": _("Adjustment (SAR)"),
            "fieldname": "adjustment",
            "fieldtype": "Currency",
            "width": 180
        },
        {
            "label": _("VAT Amount (SAR)"),
            "fieldname": "vat",
            "fieldtype": "Currency",
            "width": 180
        },
    ]