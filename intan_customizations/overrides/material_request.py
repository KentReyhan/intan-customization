import sys

import frappe
from frappe.model.document import Document


def _called_from_reorder_job():
    # Found live 2026-10-01 (MAT-MR-2026-00046 landed docstatus=1/Approved when
    # the reorder job was run manually): frappe.flags.in_reorder_job is set by
    # reorder_item_patch.py, a monkeypatch applied as a side effect of importing
    # hooks.py — but Frappe only imports hooks.py on an app_hooks CACHE MISS
    # (frappe.get_hooks caches the loaded hooks in Redis outside developer
    # mode), so a worker started while that cache is warm never applies the
    # patch and the flag is never set. This module, by contrast, is always
    # imported (it's the extend_doctype_class target), so detect the caller
    # directly instead of relying on the patch: walk the stack for ERPNext's own
    # create_material_request().
    frame = sys._getframe(2)
    while frame:
        if (
            frame.f_code.co_name == "create_material_request"
            and frame.f_globals.get("__name__") == "erpnext.stock.reorder_item"
        ):
            return True
        frame = frame.f_back
    return False


class MaterialRequestMixin(Document):
    def submit(self):
        # erpnext.stock.reorder_item.reorder_item hardcodes mr.submit() with no
        # way to opt out via Stock Settings/Workflow/REST (docs/Open-Questions.md
        # #6 in the intan-chem-erp repo). create_material_request() wraps
        # mr.insert() + mr.submit() in one try/except, so raising here to block
        # the submit would roll back the whole MR instead of leaving it as
        # Draft — this has to be a silent no-op instead.
        #
        # Leaving auto-created MRs at docstatus=0 keeps them subject to the
        # signed-off Draft -> Pending Approval -> Approved workflow instead of
        # skipping straight to Approved.
        #
        # Found live 2026-09-23: gating this on self.auto_created_via_reorder
        # alone (the field, permanent from creation) also silently swallowed a
        # Director's later legitimate Approve action on the same MR, since
        # that action calls the exact same submit() with the same field still
        # set — MAT-MR-2026-00039/00040/00041 stuck in "Pending Approval"
        # forever. reorder_item_patch.py now sets frappe.flags.in_reorder_job
        # only for the duration of the reorder job's own
        # create_material_request() call, so this only no-ops the job's
        # submit — a human approving via the workflow later goes through
        # normally.
        if self.auto_created_via_reorder and (frappe.flags.get("in_reorder_job") or _called_from_reorder_job()):
            return
        super().submit()
