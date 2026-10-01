// INTAN_SIDEBAR_TEAM_GROUPS_MARKER v1
//
// Requested directly by the user 2026-10-01 (client item #11 follow-up): the
// four per-team accordion groups in the Buying sidebar (Stock Control,
// Procurement, Eksim, Finance AP & Director — intan-chem-erp's
// dev/config.py BUYING_SIDEBAR_TEAM_GROUPS) are one shared Workspace Sidebar
// record. Frappe hides a LINK the viewer can't open, but a group HEADER always
// renders, so every role saw every team's header. A Workspace Sidebar row has
// no role/condition field, hence this small Desk script (app_include_js, see
// ../../hooks.py): it hides a team's header — and with it the whole group,
// whose links are nested inside the header's own container — unless the
// viewer holds one of that team's roles.
//
// Purely cosmetic: it never grants or removes access. Link visibility is
// still decided by Frappe's permission checks. Fails open — if the viewer's
// roles can't be read for any reason, nothing is hidden.
//
// KEEP IN SYNC BY HAND with config.BUYING_SIDEBAR_TEAM_GROUPS's labels in
// intan-chem-erp. A group label not listed here is never touched.

(function () {
    var GROUP_ROLES = {
        "Stock Control": ["Purchasing", "Procurement Manager", "Stock User", "Stock Manager", "Director"],
        "Procurement": ["Procurement Manager", "Purchasing", "Director"],
        "Eksim": ["Eksim", "Procurement Manager", "Director"],
        "Finance AP & Director": ["Finance AP", "Director"],
    };
    // Always see every group (admin accounts).
    var SEES_ALL = ["System Manager"];

    function viewer_roles() {
        if (window.frappe && Array.isArray(frappe.user_roles) && frappe.user_roles.length) return frappe.user_roles;
        if (window.frappe && frappe.boot && frappe.boot.user && Array.isArray(frappe.boot.user.roles)) {
            return frappe.boot.user.roles;
        }
        return null;
    }

    function has_any(roles, wanted) {
        return wanted.some(function (r) { return roles.indexOf(r) !== -1; });
    }

    function apply() {
        var roles = viewer_roles();
        var is_admin = window.frappe && frappe.session && frappe.session.user === "Administrator";
        var items = document.querySelectorAll(".sidebar-items .sidebar-item-container.section-item");
        for (var i = 0; i < items.length; i++) {
            var el = items[i];
            var wanted = GROUP_ROLES[el.getAttribute("item-name")];
            if (!wanted) continue;
            var show = !roles || is_admin || has_any(roles, SEES_ALL) || has_any(roles, wanted);
            var target = show ? "" : "none";
            if (el.style.display !== target) el.style.display = target;
        }
    }

    var scheduled = false;
    function schedule() {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(function () { scheduled = false; apply(); });
    }

    // The sidebar is re-rendered on workspace switches and expand/collapse, so
    // re-apply on DOM additions. childList only (not attributes): our own
    // style change must not retrigger this.
    function start() {
        new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
        apply();
    }
    if (document.body) start();
    else document.addEventListener("DOMContentLoaded", start);
})();
