from frappe.model.document import Document


class MaterialRequestMixin(Document):
    def submit(self):
        # erpnext.stock.reorder_item.reorder_item hardcodes mr.submit() with no
        # way to opt out via Stock Settings/Workflow/REST (docs/Open-Questions.md
        # #6 in the intan-chem-erp repo). create_material_request() wraps
        # mr.insert() + mr.submit() in one try/except with a DB savepoint, so
        # raising here to block the submit would roll back the whole MR instead
        # of leaving it as Draft — this has to be a silent no-op instead.
        #
        # Leaving auto-created MRs at docstatus=0 keeps them subject to the
        # signed-off Draft -> Pending Approval -> Approved workflow instead of
        # skipping straight to Approved. Human-submitted MRs are unaffected.
        if self.auto_created_via_reorder:
            return
        super().submit()
