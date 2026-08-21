# intan_customizations

Small server-side Frappe app for fixes that can't be done over REST (this
repo's usual toolchain — see `../../dev/README.md`). Currently contains one
thing: a `Material Request` override that stops ERPNext's built-in "Reorder
Item" job from skipping the approval workflow.

See `../../docs/Open-Questions.md` #6 for the full background: ERPNext's
`erpnext.stock.reorder_item.reorder_item` job hardcodes `mr.submit()` on
every auto-created Material Request, landing it at `docstatus=1`,
`workflow_state="Approved"` instead of Draft — skipping the
Draft → Pending Approval → Approved workflow both signed-off process docs
and `docs/PRD-Procurement-Module.md` §3.1 require. There is no Stock
Settings/Workflow/REST toggle for this; it needs a real server-side
override, which only became possible once production had SSH/bench access
(2026-08-21) — staging remains a locked shared bench and is **not** covered
by this app; it still relies on `dev/phase2_config/reorder_mr_draft_sweeper.py`.

`intan_customizations/overrides/material_request.py` defines
`MaterialRequestMixin`, wired in via `extend_doctype_class` (not
`override_doctype_class` — confirmed live 2026-08-21 that the "Intan
Procurement" bench group is Frappe **Version 16**, where
`extend_doctype_class` is the recommended hook: it composes as a mixin
ahead of the real controller instead of fully replacing the class). It
makes `submit()` a no-op when `auto_created_via_reorder` is set (ERPNext's
own native field). A hook that *raises* to block the submit would roll back
the entire MR — ERPNext wraps `insert()` + `submit()` in one try/except
with a savepoint — so this has to silently skip instead. Human-submitted
MRs are untouched.

## Deploy

Bench group: **Intan Procurement**, site: **production-intan-chemical.j.frappe.cloud**.

Full step-by-step (getting SSH access, why `scp` won't work over Frappe
Cloud's private-bench proxy, install, and verification) is in
**[DEPLOY.md](DEPLOY.md)**. Run entirely by you over SSH — nothing here is
executed by this repo or by Claude automatically.

Short version: push this folder to its own git repo, `bench get-app <url>`
it on the bench, `install-app` + `migrate` + `restart`, then confirm
`MaterialRequestMixin` is in the MRO of a fresh Material Request doc and
that a fresh auto-created MR lands as `docstatus=0` / `workflow_state="Draft"`.

This does **not** retroactively fix the 4 pre-existing Material Requests
that already landed wrong (`MAT-MR-2026-00002`, `00003`, `00014`, `00015`)
— those are a separate, already-made decision to leave as evidence; see
`dev/phase2_config/reorder_mr_draft_sweeper.py` if that decision changes.
