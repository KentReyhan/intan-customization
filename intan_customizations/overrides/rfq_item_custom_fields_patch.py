import frappe

# Requested directly by the user 2026-09-25: put the 9 free-text supplier-
# quote fields (product name, CAS number, MOQ, price, incoterm, payment
# term, stock ready/not, lead time, important note — see intan-chem-erp's
# dev/config.py SUPPLIER_QUOTATION_ITEM_QUOTE_FIELDS) directly on the
# built-in Supplier Portal's /rfq/<name> page, not (only) on a separate
# Web Form.
#
# Confirmed live by reading ERPNext v16.32.3's actual source
# (erpnext/templates/pages/rfq.js + erpnext/buying/doctype/
# request_for_quotation/request_for_quotation.py): the /rfq/<name> page
# ships the WHOLE RFQ doc to the browser as `window.doc` (Jinja
# `{{ doc.as_json() }}`), and clicking "Make Quotation" posts that entire
# object to the whitelisted `create_supplier_quotation`, which internally
# calls `create_rfq_items()` per item — but that function only copies an
# EXPLICIT allowlist of fields (item_code, item_name, description, qty,
# rate, conversion_factor, warehouse, material_request,
# material_request_item, stock_qty, uom) onto the new Supplier Quotation
# Item row. Any custom field present in the posted item dict (which the
# paired ../public/js/rfq_portal_custom_fields.js adds via DOM injection,
# no template override needed) is silently dropped without this patch.
#
# Deliberately NOT overriding rfq_items.html / rfq.js directly: those are
# Jinja includes shared at the same relative path with erpnext's own
# templates, and this project has no confirmed precedent for how Frappe's
# multi-app template-loader precedence resolves a collision there — could
# not be verified without the very SSH deploy this app requires (see
# DEPLOY.md), so it wasn't worth the risk. A plain module-level monkeypatch
# (this file) is the same proven, deterministic mechanism already used by
# reorder_item_patch.py in this app, and web_include_js (see hooks.py) for
# the client side is a documented, unambiguous Frappe hook — neither
# depends on template-path precedence at all.
import erpnext.buying.doctype.request_for_quotation.request_for_quotation as _rfq_module

CUSTOM_ITEM_FIELDS = [
    "custom_product_name",
    "custom_cas_number",
    "custom_moq",
    "custom_quoted_price",
    "custom_stock_status",
    "custom_incoterm",
    "custom_payment_term",
    "custom_lead_time_note",
    "custom_important_note",
]

if not getattr(_rfq_module, "_intan_create_rfq_items_patched", False):
    _original_create_rfq_items = _rfq_module.create_rfq_items

    def _create_rfq_items_with_custom_fields(sq_doc, supplier, data):
        _original_create_rfq_items(sq_doc, supplier, data)
        # The original just appended a new row as the last item — update it
        # in place with whatever of the 9 custom fields the client sent.
        row = sq_doc.items[-1]
        for fieldname in CUSTOM_ITEM_FIELDS:
            value = data.get(fieldname)
            if value:
                row.set(fieldname, value)

    _rfq_module.create_rfq_items = _create_rfq_items_with_custom_fields
    _rfq_module._intan_create_rfq_items_patched = True
