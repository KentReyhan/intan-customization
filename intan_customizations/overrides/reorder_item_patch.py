import frappe

# Found live 2026-09-23: MaterialRequestMixin.submit() (material_request.py)
# no-ops submit() whenever auto_created_via_reorder=1, with no way to tell
# "the reorder job itself is calling this" apart from "a Director is later
# approving this same MR via the normal workflow" — both submit() calls hit
# the same doctype-level check on the same field, so the no-op that was
# meant to stop the *job* from skipping approval also permanently blocked
# the *workflow's own Approve action* on every MR that started out
# auto-created. Confirmed live: MAT-MR-2026-00039/00040/00041 all stuck in
# workflow_state="Pending Approval" with docstatus=0 no matter how many
# times Director clicked Approve — the workflow engine sets
# workflow_state="Approved" in memory then calls submit(), which silently
# did nothing, so the next page load showed the DB's real (unsubmitted)
# state instead.
#
# Fix: stop keying off the field (which is permanent, set once at MR
# creation) and key off *who is calling submit()* instead. Wrap ERPNext's
# own erpnext.stock.reorder_item.create_material_request — the one place
# that hardcodes mr.insert() + mr.submit() with no override hook (see
# ../README.md and docs/Open-Questions.md #6) — with a frappe.flags marker
# for the duration of that call only. material_request.py's submit()
# override now checks that flag, not just the field, so a later human
# Approve (a completely separate request, with the flag unset) goes
# through normally.
import erpnext.stock.reorder_item as _reorder_item_module

if not getattr(_reorder_item_module, "_intan_create_material_request_patched", False):
    _original_create_material_request = _reorder_item_module.create_material_request

    def _create_material_request_marking_reorder_job(material_requests):
        frappe.flags.in_reorder_job = True
        try:
            return _original_create_material_request(material_requests)
        finally:
            frappe.flags.in_reorder_job = False

    _reorder_item_module.create_material_request = _create_material_request_marking_reorder_job
    _reorder_item_module._intan_create_material_request_patched = True
