# intan_customizations

Small server-side Frappe app for fixes that can't be done over REST (this
repo's usual toolchain — see `../../dev/README.md`). Started as one thing —
a `Material Request` override that stops ERPNext's built-in "Reorder Item"
job from skipping the approval workflow — and has since picked up a
`Supplier Quotation` submit-time gate, a `Purchase Order` cancel-workflow
guard (both wired via `extend_doctype_class` in `hooks.py`, not documented
in detail below yet), and, as of 2026-09-25, a pair of overrides that put
supplier-quote fields directly on the built-in Supplier Portal's
`/rfq/<name>` page (see that section further down).

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
own native field) **and** the call is coming from the reorder job itself. A
hook that *raises* to block the submit would roll back the entire MR —
ERPNext wraps `insert()` + `submit()` in one try/except — so this has to
silently skip instead.

**Found live 2026-09-23**: gating the no-op on the field alone (not who's
calling) also permanently blocked a Director's *later* legitimate Approve
action on the same MR — Approve calls the exact same `submit()`, and the
field never gets unset, so every auto-reorder-created MR was stuck in
"Pending Approval" forever, with no way to approve it
(`MAT-MR-2026-00039`/`00040`/`00041`). Fixed by
`overrides/reorder_item_patch.py`, which wraps ERPNext's own
`erpnext.stock.reorder_item.create_material_request` (the one place that
calls `mr.insert()` + `mr.submit()`) to set `frappe.flags.in_reorder_job`
only for the duration of that call. `submit()` now only no-ops when *both*
the field is set *and* that flag is set — a Director approving later, in a
separate request with the flag unset, submits normally.

## RFQ portal supplier-quote fields (2026-09-25)

Requested directly by the user: 9 free-text fields (product name, CAS
number, MOQ, price, incoterm, payment term, stock ready/not, lead time,
important note — same list as `../../dev/config.py`'s
`SUPPLIER_QUOTATION_ITEM_QUOTE_FIELDS`) on the built-in Supplier Portal's
`/rfq/<name>` page, where a supplier reviews an RFQ and clicks
"Make Quotation." These already exist as real Custom Fields on Supplier
Quotation Item (deployed over REST, no SSH needed — see
`dev/phase2_config/supplier_quotation_item_free_text_fields.py`); this app
is what actually gets them *onto that specific page* and makes sure they
*persist* when a supplier submits.

Two pieces, both required together:
- `overrides/rfq_item_custom_fields_patch.py` — monkeypatches ERPNext's
  own `create_rfq_items()` (in
  `erpnext.buying.doctype.request_for_quotation.request_for_quotation`),
  which otherwise silently drops these 9 fields even if the browser sends
  them, since it only copies an explicit allowlist of standard fields onto
  the new Supplier Quotation Item row.
- `public/js/rfq_portal_custom_fields.js` — shipped via the `web_include_js`
  hook, injects the 9 input fields into each item row on `/rfq/<name>` via
  DOM manipulation and keeps them in sync with the same `window.doc`
  object ERPNext's own `rfq.js` already maintains for qty/rate.

Deliberately **not** implemented by overriding ERPNext's shipped
`rfq_items.html`/`rfq.js` templates directly, even though that would look
like the more obvious fix: those live at a template path shared with
erpnext, and this project has no confirmed precedent for how Frappe
resolves a same-path collision across multiple installed apps — untestable
without the SSH deploy itself, so not worth the risk. The monkeypatch +
`web_include_js` combination sidesteps that question entirely; both are
well-precedented, unambiguous Frappe mechanisms.

This is the one part of the whole feature that couldn't be verified before
deploying — everything else (the Custom Fields themselves, a separate
`supplier-quotation-response` Web Form, and the Supplier role's
permissions) was tested live via REST and Playwright in the main repo.
**[DEPLOY.md](DEPLOY.md)'s "2026-09-25 update" section has the exact
post-deploy verification steps — run them, don't just assume this worked.**

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
