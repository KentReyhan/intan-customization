app_name = "intan_customizations"
app_title = "Intan Customizations"
app_publisher = "Intan Chemical"
app_description = "Server-side ERPNext overrides for Intan Chemical that can't be done over REST"
app_email = "developer@mistorchen.com"
app_license = "mit"

# See docs/Open-Questions.md #6 in the intan-chem-erp repo: ERPNext's
# "Reorder Item" job (erpnext.stock.reorder_item.reorder_item) hardcodes
# mr.submit() on auto-created Material Requests, skipping the signed-off
# Draft -> Pending Approval -> Approved workflow entirely. There's no
# Stock Settings/Workflow/REST toggle for this — it needs a server-side
# override, which is what this app exists for.
#
# extend_doctype_class (not override_doctype_class) — confirmed live 2026-08-21
# that the "Intan Procurement" bench group on Frappe Cloud is Frappe
# Framework Version 16, where extend_doctype_class is the recommended hook:
# it composes as a mixin ahead of the real controller in the MRO instead of
# fully replacing the class, so it can't clobber another app's override of
# Material Request (confirmed none exists in erpnext's own hooks.py anyway,
# but this is safer regardless).
# Importing this applies its monkeypatch as a side effect (wraps
# erpnext.stock.reorder_item.create_material_request to set
# frappe.flags.in_reorder_job around its own insert()+submit() call — see
# overrides/reorder_item_patch.py and material_request.py's submit()
# override for why). hooks.py is guaranteed to be imported for every app on
# every worker/request, so this runs before any scheduled job or REST call
# can reach reorder_item.create_material_request.
from intan_customizations.overrides import reorder_item_patch  # noqa: F401

# Requested directly by the user 2026-09-25: put the 9 free-text supplier-
# quote fields on the built-in Supplier Portal's /rfq/<name> page. See
# overrides/rfq_item_custom_fields_patch.py's own header for the full
# reasoning and why this is a module-level monkeypatch (matching
# reorder_item_patch.py's existing pattern) rather than an attempt to
# override erpnext's rfq_items.html/rfq.js templates directly — this
# project has no confirmed precedent for multi-app Jinja-include override
# precedence, and it couldn't be verified without this very SSH deploy.
from intan_customizations.overrides import rfq_item_custom_fields_patch  # noqa: F401

# Client-side half of the same feature — see public/js/rfq_portal_custom_
# fields.js's own header. web_include_js loads this on every website/
# portal page (guarded internally to only act on /rfq/<name>), which is a
# documented, unambiguous Frappe hook — unlike overriding a shared
# template path, there's no cross-app precedence question here.
#
# MUST be the full /assets/<app>/js/<file> path, not a bare filename —
# confirmed live 2026-09-25 (first deploy of this feature): a bare
# filename here renders as <script src="rfq_portal_custom_fields.js">,
# resolved by the browser against the CURRENT PAGE's own URL
# (/rfq/<name>), not against /assets/, so it 404s and the browser refuses
# to execute the HTML error page it gets back instead ("Refused to
# execute script ... MIME type ('text/html') is not executable"). Unlike
# app_include_js (Desk app), web_include_js does not appear to prefix a
# bare filename with /assets/<app>/js/ automatically.
web_include_js = "/assets/intan_customizations/js/rfq_portal_custom_fields.js"

extend_doctype_class = {
    "Material Request": ["intan_customizations.overrides.material_request.MaterialRequestMixin"],
    # Server-side backstop for the Sample QC submit gate — the Client Script
    # version (quality_inspection_sample_qc_trigger_script.js) only runs
    # through the Desk UI, so a Supplier Portal auto-submitted quotation
    # skipped it entirely. See docs/Open-Questions.md in intan-chem-erp.
    "Supplier Quotation": ["intan_customizations.overrides.supplier_quotation.SupplierQuotationMixin"],
    # Blocks a direct/native Cancel that bypasses the gated Cancel workflow
    # (Initiate Cancel -> Execute Cancel -> Approve Cancel) — Director's
    # cancel:1 DocPerm, needed for the workflow's own final transition, also
    # exposes the plain native Cancel button/API call as a way around it.
    "Purchase Order": ["intan_customizations.overrides.purchase_order.PurchaseOrderMixin"],
}
