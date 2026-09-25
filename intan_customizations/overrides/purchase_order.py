import frappe
from frappe.model.document import Document

# dev/config.py's PO_CANCEL_APPROVAL_STATE. Not imported directly — this app
# has no dependency on the intan-chem-erp REST deploy-script repo's config
# module, same isolation as MaterialRequestMixin — so the value is inlined
# and must be kept in sync by hand if that constant's value ever changes.
PO_CANCEL_APPROVAL_STATE = "Pending Cancel Director Approval"


class PurchaseOrderMixin(Document):
    def before_cancel(self):
        # Only the Cancel workflow's own final "Approve Cancel" transition
        # may reach docstatus=2 — apply_workflow() calls doc.cancel() itself
        # once that transition's target state has doc_status="2" (see
        # dev/config.py:367-372 in intan-chem-erp). Director holds a
        # doctype-level cancel:1 DocPerm so that click succeeds (see
        # po_cancel_workflow_director_permission.py there) — but that same
        # permission also exposes the plain native "Cancel" menu item,
        # letting Director bypass the whole Initiate -> Execute -> Approve
        # chain (no reason captured, no check) directly from the Desk UI or
        # a raw API call. Blocking any cancel attempted from outside the
        # workflow's own approval state closes that gap at the only point
        # that's actually authoritative for every path, not just the Desk UI.
        if self.workflow_state != PO_CANCEL_APPROVAL_STATE:
            frappe.throw(
                "Cancel is only allowed via the Purchase Order Cancel workflow "
                "(Initiate Cancel → Execute Cancel → Approve Cancel)."
            )
