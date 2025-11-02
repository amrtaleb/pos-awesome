"""
POS Status Tracker API
Path: frappe-bench/apps/posawesome/posawesome/posawesome/api/pos_status_tracker.py
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_sales_invoices(filters=None):
    """
    Get Sales Invoices using:
    - customer_mobile (search in Address.phone / Address.mobile_no)
    - invoice_id

    Return phone number from Address (not from Sales Invoice).
    """
    try:
        conditions = ["si.docstatus = 1"]  # Only submitted invoices
        values = {}

        if filters:
            import json
            if isinstance(filters, str):
                filters = json.loads(filters)

            # Search by phone -> match customer via Address -> Dynamic Link
            if filters.get("customer_mobile"):
                conditions.append("""
                    si.customer IN (
                        SELECT dl.link_name 
                        FROM `tabAddress` addr
                        INNER JOIN `tabDynamic Link` dl ON dl.parent = addr.name
                        WHERE dl.link_doctype = 'Customer'
                        AND (addr.phone LIKE %(mobile)s )
                    )
                """)
                values["mobile"] = f"%{filters['customer_mobile']}%"

            # Search by invoice ID
            if filters.get("invoice_id"):
                conditions.append("si.name = %(invoice_id)s")
                values["invoice_id"] = filters["invoice_id"]

        where_clause = " AND ".join(conditions)

        invoices = frappe.db.sql(f"""
            SELECT 
                si.name AS invoice_id,
                si.customer,
                si.customer_name,
                si.posting_date,
                si.grand_total,
                si.pos_status,
                si.status,
                (
                    SELECT addr.phone
                    FROM `tabAddress` addr
                    INNER JOIN `tabDynamic Link` dl ON dl.parent = addr.name
                    WHERE dl.link_doctype = 'Customer'
                    AND dl.link_name = si.customer
                    LIMIT 1
                ) AS customer_phone
            FROM `tabSales Invoice` si
            WHERE {where_clause}
            ORDER BY si.posting_date DESC, si.creation DESC
            LIMIT 100
        """, values=values, as_dict=1)

        return {
            "success": True,
            "data": invoices
        }

    except Exception as e:
        frappe.log_error(f"Error in get_sales_invoices: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def update_pos_status(invoice_id, new_status):
    """
    Update POS status for a sales invoice
    """
    try:
        if not invoice_id or not new_status:
            frappe.throw(_("Invoice ID and Status are required"))

        # Validate status
        valid_statuses = ["Received", "Delivered", "Ready", "Under Delivery", "Washing and Ironing"]
        if new_status not in valid_statuses:
            frappe.throw(_("Invalid status"))

        # Check if invoice exists
        if not frappe.db.exists("Sales Invoice", invoice_id):
            frappe.throw(_("Sales Invoice not found"))

        # Update status
        doc = frappe.get_doc("Sales Invoice", invoice_id)

        # Check permissions
        if not doc.has_permission("write"):
            frappe.throw(_("Insufficient permissions to update this invoice"))

        old_status = doc.pos_status
        doc.pos_status = new_status
        doc.add_comment("Comment", f"POS Status changed from '{old_status}' to '{new_status}'")
        doc.save(ignore_permissions=False)

        frappe.db.commit()

        return {
            "success": True,
            "message": _("Status updated successfully"),
            "invoice_id": invoice_id,
            "old_status": old_status,
            "new_status": new_status
        }

    except Exception as e:
        frappe.log_error(f"Error in update_pos_status: {str(e)}")
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_status_summary():
    """
    Get summary count of invoices by status
    """
    try:
        summary = frappe.db.sql("""
            SELECT 
                COALESCE(pos_status, 'Not Set') as status,
                COUNT(*) as count,
                SUM(grand_total) as total_amount
            FROM `tabSales Invoice`
            WHERE docstatus = 1
            GROUP BY pos_status
            ORDER BY count DESC
        """, as_dict=1)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        frappe.log_error(f"Error in get_status_summary: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }