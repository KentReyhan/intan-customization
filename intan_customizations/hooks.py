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
extend_doctype_class = {
    "Material Request": ["intan_customizations.overrides.material_request.MaterialRequestMixin"]
}
