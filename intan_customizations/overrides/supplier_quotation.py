import frappe
from frappe.model.document import Document

# Mirrors get_rows_needing_inspection() in
# dev/phase2_config/quality_inspection_sample_qc_trigger_script.js — keep
# both in sync. That Client Script's own before_submit gate only runs
# through the Desk UI; a Supplier Quotation submitted via another path (the
# Supplier Portal's auto-submit-on-reply flow, docs/uat/UAT-05-rfq-email-
# supplier-portal.md) skips it entirely. before_submit is the correct
# server-side hook to mirror it on: it fires for every submit path (Desk UI,
# REST, Portal), unlike validate, which fires on every save including a
# plain Draft (same distinction the Client Script's own header comment
# worked out the hard way — see PUR-SQTN-2026-00013).
SAMPLE_QC_NOT_ACCEPTED_MSG = (
    "Cannot submit: <b>{0}</b> requires an Accepted sample Quality Inspection first. "
    "Use \"Create &gt; Quality Inspection\" on this quotation to record and accept one."
)


class SupplierQuotationMixin(Document):
    def before_submit(self):
        rows_without_mr_override = [r for r in self.items if not r.material_request_item]
        item_codes = {r.item_code for r in rows_without_mr_override if r.item_code}

        globally_required = set()
        if item_codes:
            globally_required = set(frappe.db.get_all(
                "Item",
                filters={"name": ["in", list(item_codes)], "inspection_required_before_purchase": 1},
                pluck="name",
            ))

        relevant_rows = [
            r for r in self.items
            if (r.custom_needs_sample_override if r.material_request_item else r.item_code in globally_required)
        ]
        if not relevant_rows:
            return

        # order_by + first-wins: a row can have MORE THAN ONE Quality
        # Inspection (a Rejected one plus a retry, per the user's 2026-09-15
        # request that a Rejected sample must be re-triable) — gate on the
        # NEWEST one's status, matching quality_inspection_sample_qc_
        # trigger_script.js's own identical fix (a plain dict() of an
        # unordered query result picked an arbitrary one, not necessarily
        # the newest — same bug class, ported here from that script).
        qi_status_by_row = {}
        for qi in frappe.db.get_all(
            "Quality Inspection",
            filters={"custom_supplier_quotation": self.name},
            fields=["custom_supplier_quotation_item", "status"],
            order_by="creation desc",
        ):
            if qi.custom_supplier_quotation_item and qi.custom_supplier_quotation_item not in qi_status_by_row:
                qi_status_by_row[qi.custom_supplier_quotation_item] = qi.status

        for row in relevant_rows:
            if qi_status_by_row.get(row.name) != "Accepted":
                frappe.throw(SAMPLE_QC_NOT_ACCEPTED_MSG.format(frappe.utils.escape_html(row.item_code)))
