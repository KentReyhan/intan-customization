import frappe

# 2026-09-03 — Frappe's own "Notification" doctype (channel="System
# Notification", receiver_by_role) was confirmed live on this site to only
# ever deliver a Notification Log entry to the user who performed the
# triggering action, never to other users holding the same role — tested
# with three different real accounts (financeap@example.com,
# director@example.com, and a freshly created real-domain test account),
# none of which ever received anything despite holding the correct role the
# whole time. Root cause not identifiable without bench source access at
# the time this was written; this hook creates the Notification Log
# directly instead of relying on that mechanism, so it isn't affected by
# whatever's broken there.
#
# Mirrors dev/config.py's WORKFLOW_STAGE_NOTIFICATIONS (Purchase Order /
# Material Request pending-approval states) and PO_APPROVED_NOTIFICATION_*
# (Eksim, on final Approval) in the intan-chem-erp repo — kept in sync by
# hand, since this app is a separate deployed package. The original
# "Notification" doctype records are left in place (harmless/redundant,
# still occasionally firing for the acting user) rather than removed.
#
# Does NOT cover the two "Days After" (schedule-based, not doc-save-based)
# notifications — PO_OVERDUE_NOTIFICATION and EKSIM_GATE1_OVERDUE_NOTIFICATION
# — likely need the same fix via a scheduled_tasks hook instead; not done
# here, flagged as a separate follow-up.

WORKFLOW_STATE_NOTIFICATIONS = {
    "Purchase Order": {
        "Pending Finance AP Approval": ("Finance AP", "Purchase Order {0} awaiting your approval"),
        "Pending Director Approval": ("Director", "Purchase Order {0} awaiting your approval"),
        "Pending Close Finance AP Approval": ("Finance AP", "Purchase Order {0} awaiting close execution"),
        "Pending Close Director Approval": ("Director", "Purchase Order {0} awaiting close approval"),
    },
    "Material Request": {
        "Pending Approval": ("Director", "Material Request {0} awaiting your approval"),
    },
}


def _notify_role(doc, role, subject):
    users = frappe.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        pluck="parent",
    )
    if not users:
        return
    enabled_system_users = set(
        frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name")
    )
    for user in users:
        if user not in enabled_system_users:
            continue
        notification = frappe.new_doc("Notification Log")
        notification.for_user = user
        notification.type = "Alert"
        notification.document_type = doc.doctype
        notification.document_name = doc.name
        notification.subject = subject
        notification.from_user = frappe.session.user
        notification.insert(ignore_permissions=True)


def notify_on_workflow_state_change(doc, method=None):
    """doc_events on_update hook for Purchase Order / Material Request."""
    before = doc.get_doc_before_save()
    old_state = before.get("workflow_state") if before else None
    new_state = doc.get("workflow_state")
    if old_state == new_state:
        return

    entry = WORKFLOW_STATE_NOTIFICATIONS.get(doc.doctype, {}).get(new_state)
    if not entry:
        return
    role, subject_template = entry
    _notify_role(doc, role, subject_template.format(doc.name))


def notify_po_approved(doc, method=None):
    """doc_events on_submit hook for Purchase Order — mirrors
    PO_APPROVED_NOTIFICATION (channel=System Notification, event=Submit,
    receiver_by_role=Eksim) in dev/config.py."""
    _notify_role(doc, "Eksim", f"Purchase Order {doc.name} Approved")
