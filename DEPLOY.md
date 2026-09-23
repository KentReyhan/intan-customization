# Deploying `intan_customizations` to the production private bench

Everything below is run **by you**, over SSH — nothing here is executed by
Claude/this repo automatically. Background: `docs/Open-Questions.md` #6.

## 0. Get SSH access to the private bench

Frappe Cloud's private-bench SSH is certificate-based and short-lived (6
hours per certificate) — and its proxy does **not** support `scp` or VS
Code Remote-SSH, only interactive shell. That's why the app gets deployed
via git (step 2) rather than copied over directly.

1. Generate a local SSH key pair if you don't already have one:
   ```bash
   ssh-keygen -t rsa -b 4096
   ```
2. In the Frappe Cloud dashboard: **Settings → SSH Key → "Add SSH Key"** —
   paste your public key (`~/.ssh/id_rsa.pub`; on macOS, `pbcopy < ~/.ssh/id_rsa.pub`
   copies it for you).
3. Go to your **bench group** dashboard (**Intan Procurement**) → click the
   **⋮** (three dots) next to it. If "SSH Access" isn't a direct item there,
   check under **"Bench Actions"** first, or open the bench group's own page
   (click "Intan Procurement" itself) for a fuller settings view — then
   **"Generate SSH Certificate"**.
4. Copy the commands shown in the dialog and run them in your terminal —
   this installs a certificate next to your private key (e.g.
   `id_rsa-cert.pub` alongside `id_rsa`). It's valid for 6 hours; you'll
   repeat steps 3–4 whenever it expires.
5. Connect with the exact command the dialog gives you, shaped like:
   ```bash
   ssh <bench-group-name>@<region>.frappe.cloud -p 2222
   ```

You should land in a shell with a `frappe-bench` directory.

## 1. Get the app's code somewhere `bench get-app` can reach

Since `scp` doesn't work over this proxy, push `bench_apps/intan_customizations`
to its own git repo first (from your Mac, **not** over the bench SSH
session):

```bash
cd bench_apps/intan_customizations
git init
git add .
git commit -m "intan_customizations: Material Request draft-on-reorder fix"
git remote add origin <url-of-a-new-empty-repo-you-create>
git push -u origin main
```

Create that empty repo on GitHub (or wherever) first — private is fine, as
long as the bench server can clone it (use an HTTPS URL with a token, or
add a deploy key, if private).

## 2. On the bench (inside the SSH session)

```bash
cd frappe-bench
```

### Pre-flight check — don't skip this

```bash
grep -n "override_doctype_class\|extend_doctype_class" apps/erpnext/erpnext/hooks.py
```
This should print nothing mentioning `Material Request`. If it does, stop
and tell Claude — ERPNext already overrides/extends that class and ours
could conflict.

(The Frappe-version check that used to live here is resolved: the "Intan
Procurement" bench group is confirmed **Version 16**, so `hooks.py` already
uses `extend_doctype_class` — no branch to pick at deploy time.)

### Install the app

```bash
bench get-app <url-of-the-repo-from-step-1>
bench --site production-intan-chemical.j.frappe.cloud install-app intan_customizations
bench --site production-intan-chemical.j.frappe.cloud migrate
bench restart
```

## 3. Verify the override loaded

```bash
bench --site production-intan-chemical.j.frappe.cloud console
```
Inside the Python console:
```python
>>> from intan_customizations.overrides.material_request import MaterialRequestMixin
>>> mr = frappe.get_doc({"doctype": "Material Request"})
>>> isinstance(mr, MaterialRequestMixin)
```
Expect `True`. (With `extend_doctype_class`, the runtime class is a
dynamically composed mixin — its `__class__.__name__` isn't a fixed string
to check against, so `isinstance` against the mixin is the reliable check.)
Then `exit()`.

## 4. Verify the actual behavior

Two options:
- **Wait** for the job's normal 06:00 run, then check the newest
  auto-created MR is `docstatus=0` / `workflow_state="Draft"`.
- **Force it now** via Desk UI: Scheduled Job Type →
  `erpnext.stock.reorder_item.reorder_item` → **Execute**. Only do this if
  you're fine with it touching real items currently below reorder level
  (per `docs/Open-Questions.md` #6, `2700003`/`SKU010` may already
  qualify). Ask first if you'd rather test against a throwaway item.

## 5. Report back

Once steps 3–4 are confirmed, let Claude know so `docs/Open-Questions.md`
#6 can be updated from "pending deploy" to resolved (with the date).

**Does not** retroactively fix the 4 pre-existing bad MRs
(`MAT-MR-2026-00002`/`00003`/`00014`/`00015`) — that's a separate,
already-made decision to leave them as evidence; see
`dev/phase2_config/reorder_mr_draft_sweeper.py` if that decision changes.

## Updating an already-installed app

Once the app is already installed on production, a later code change is an
update, not a fresh install — skip `bench get-app`/`install-app` and just
pull the new commit onto the already-cloned app.

**From your Mac** (in `bench_apps/intan_customizations`):
```bash
git add .
git commit -m "<describe the change>"
git push origin main
```

**Over the same SSH session as before** (`ssh <bench-group-name>@<region>.frappe.cloud -p 2222`):
```bash
cd frappe-bench/apps/intan_customizations
git pull origin main
cd ../..
bench --site production-intan-chemical.j.frappe.cloud migrate
bench restart
```

**2026-09-23 fix — verify after this specific update**: once deployed,
confirm a Director can now actually approve an MR stuck from the earlier
bug. Easiest via Desk UI: open `MAT-MR-2026-00039` (or `00040`/`00041`) as
the Director user and click Approve — it should move to `workflow_state=
"Approved"`, `docstatus=1`, and *stay* there on reload (not bounce back to
"Pending Approval"). If you'd rather verify from a console first:
```python
>>> from intan_customizations.overrides import reorder_item_patch
>>> import erpnext.stock.reorder_item as ri
>>> ri.create_material_request.__name__
```
Expect `'_create_material_request_marking_reorder_job'`, not
`'create_material_request'` — confirms the monkeypatch applied.

Note: this bench group's own deploy step has been observed to commit
compiled `__pycache__/*.pyc` files into this repo as a side effect — those
are harmless but shouldn't be treated as real changes when reviewing
`git log` here.

**2026-09-03 note**: a `doc_events` hook was briefly added and then removed
here to work around what looked like a broken "notify by role" mechanism in
Frappe's own Notification doctype. That diagnosis turned out to be wrong —
see `docs/Production-Runbook.md`-adjacent history in the main
`intan-chem-erp` repo for the full story — Frappe's built-in mechanism was
working correctly the whole time; the apparent failure was an artifact of
checking via a REST API key, which cannot see another user's private
Notification Log rows. No server-side fix was needed.

## Caveat: this may not survive a future Frappe Cloud dashboard deploy

Frappe Cloud's supported way to add an app to a private bench group is
attaching a git repo as an "App Source" through the dashboard, so it's
tracked and redeployed consistently. Installing via raw SSH `bench
get-app`/`install-app` works today, but if you later trigger a rebuild
from the dashboard, double check `intan_customizations` is still listed
under the bench group's apps — if it's gone, the repo from step 1 can be
re-attached as a proper App Source instead of repeating this by hand.
