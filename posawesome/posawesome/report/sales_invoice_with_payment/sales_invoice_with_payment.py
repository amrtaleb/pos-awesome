# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    # Static columns
    columns = [
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 150
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180
        },
        {
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Amount Before VAT"),
            "fieldname": "net_total",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("VAT Amount"),
            "fieldname": "total_taxes_and_charges",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Outstanding Amount"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "width": 140
        }
    ]
    
    # Get all payment modes dynamically
    payment_modes = frappe.db.sql("""
        SELECT DISTINCT sip.mode_of_payment 
        FROM `tabSales Invoice Payment` sip
        WHERE sip.mode_of_payment IS NOT NULL
        ORDER BY sip.mode_of_payment
    """, as_list=1)
    
    # Add dynamic columns for each payment mode
    for mode in payment_modes:
        if mode[0]:
            columns.append({
                "label": _(mode[0]),
                "fieldname": mode[0].lower().replace(" ", "_"),
                "fieldtype": "Currency",
                "width": 120
            })
    
    # Add status column at the end
    columns.append({
        "label": _("Status"),
        "fieldname": "status",
        "fieldtype": "Data",
        "width": 100
    })
    
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get invoice data
    invoice_data = frappe.db.sql("""
        SELECT 
            si.name as sales_invoice,
            si.posting_date,
            si.customer,
            si.customer_name,
            si.net_total,
            si.total_taxes_and_charges,
            si.grand_total,
            si.outstanding_amount,
            si.status
        FROM 
            `tabSales Invoice` si
        WHERE 
            si.docstatus = 1
            {conditions}
        ORDER BY 
            si.posting_date DESC, si.name
    """.format(conditions=conditions), filters, as_dict=1)
    
    # Get payment details for all invoices
    payment_data = frappe.db.sql("""
        SELECT 
            sip.parent as invoice,
            sip.mode_of_payment,
            sip.amount
        FROM 
            `tabSales Invoice Payment` sip
        INNER JOIN
            `tabSales Invoice` si ON si.name = sip.parent
        WHERE 
            si.docstatus = 1
            {conditions}
    """.format(conditions=conditions), filters, as_dict=1)
    
    # Create a dictionary to map invoice to payment modes
    payment_map = {}
    for payment in payment_data:
        if payment.invoice not in payment_map:
            payment_map[payment.invoice] = {}
        
        mode_key = payment.mode_of_payment.lower().replace(" ", "_")
        if mode_key in payment_map[payment.invoice]:
            payment_map[payment.invoice][mode_key] += payment.amount
        else:
            payment_map[payment.invoice][mode_key] = payment.amount
    
    # Merge invoice data with payment data
    for row in invoice_data:
        if row.sales_invoice in payment_map:
            row.update(payment_map[row.sales_invoice])
    
    return invoice_data

def get_conditions(filters):
    conditions = []
    
    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")
    
    if filters.get("customer"):
        conditions.append("si.customer = %(customer)s")
    
    if filters.get("status"):
        conditions.append("si.status = %(status)s")
    
    return " AND " + " AND ".join(conditions) if conditions else ""