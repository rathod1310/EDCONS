"""Shop-floor automation: logs update Job Cards, Furnace Heat, Pattern and stock.

Every posting runs inside a savepoint. A failure is written to the source
document's "Posting Status" and shown to the user, but never blocks the
operator's submit. Supervisors can press "Retry ERP Posting" later.
"""
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, nowtime

OK, WARN = "✔", "⚠"


def get_settings():
	return frappe.get_cached_doc("Foundry Settings")


# ---------------------------------------------------------------- validation
def validate_heat(heat, idx):
	if heat and frappe.db.get_value("Furnace Heat", heat, "docstatus") != 1:
		frappe.throw(_("Row {0}: Heat {1} is not submitted yet").format(idx, heat))


def validate_work_order(work_order, item_code, idx):
	if not work_order:
		return
	wo = frappe.db.get_value("Work Order", work_order, ["production_item", "docstatus", "status"], as_dict=True)
	if not wo:
		frappe.throw(_("Row {0}: Work Order {1} not found").format(idx, work_order))
	if item_code and wo.production_item != item_code:
		frappe.throw(_("Row {0}: Work Order {1} is for {2}, not {3}").format(idx, work_order, wo.production_item, item_code))
	if wo.docstatus != 1 or wo.status in ("Stopped", "Closed", "Cancelled"):
		frappe.throw(_("Row {0}: Work Order {1} is {2}").format(idx, work_order, wo.status))


def parse_weights(text):
	if not text:
		return []
	return [flt(x) for x in re.split(r"[,\s;/]+", text.strip()) if flt(x) > 0]


# ---------------------------------------------------------------- sand
def get_sand_limits(mould_type):
	return {r.parameter: r for r in get_settings().sand_limits if r.mould_type == mould_type}


SAND_FIELDS = {
	"Moisture": "moisture_pct",
	"Compactability": "compactability_pct",
	"GCS": "gcs",
	"Permeability": "permeability",
	"Mould Hardness": "mould_hardness",
}


def sand_row_has_values(row):
	return any(flt(row.get(f)) for f in SAND_FIELDS.values())


def check_sand_row(row, limits):
	fails = []
	for param, field in SAND_FIELDS.items():
		value, lim = flt(row.get(field)), limits.get(param)
		if not value or not lim:
			continue
		if (flt(lim.min_value) and value < flt(lim.min_value)) or (flt(lim.max_value) and value > flt(lim.max_value)):
			fails.append(param)
	return fails


# ---------------------------------------------------------------- helpers
def _status(doc, lines):
	text = "\n".join(lines) if lines else f"{OK} Nothing to post"
	doc.db_set("erp_posting_status", text, update_modified=False)
	warnings = [l for l in lines if l.startswith(WARN)]
	if warnings:
		frappe.msgprint("<br>".join(warnings), title=_("Some ERP postings need attention"), indicator="orange")


def _run(lines, label, fn):
	"""Run fn inside a savepoint; record the outcome in lines."""
	sp = "foundry_" + frappe.generate_hash(length=8)
	frappe.db.savepoint(sp)
	try:
		msg = fn()
		if msg:
			lines.append(msg)
	except Exception as e:
		frappe.db.rollback(save_point=sp)
		frappe.clear_last_message()
		lines.append(f"{WARN} {label}: {frappe.utils.strip_html(str(e))[:200]}")
		frappe.log_error(title=f"Foundry posting: {label}")


def _ref(doc):
	return f"{doc.doctype}:{doc.name}"


# ---------------------------------------------------------------- job cards
def post_job_cards(doc, total_field, good_field):
	settings = get_settings()
	lines = []
	if not cint(settings.auto_post_job_cards):
		_status(doc, [f"{OK} Job Card posting is switched off in Foundry Settings"])
		return
	ops = [r for r in settings.operation_map if r.posted_from == doc.doctype]
	if not ops:
		_status(doc, [f"{WARN} No operations mapped to {doc.doctype} in Foundry Settings"])
		return

	per_wo = {}
	for row in doc.items:
		if not row.work_order:
			continue
		d = per_wo.setdefault(row.work_order, {"Total": 0, "Good": 0, "heats": set(), "employee": None})
		d["Total"] += cint(row.get(total_field))
		d["Good"] += cint(row.get(good_field))
		if row.get("heat"):
			d["heats"].add(row.heat)
		d["employee"] = d["employee"] or row.get("moulder") or row.get("worker")

	if not per_wo:
		lines.append(f"{OK} No Work Order on any row, Job Cards not touched")
	when = get_datetime(f"{doc.posting_date} {nowtime()}")
	for wo, d in per_wo.items():
		_run(lines, f"Work Order {wo}", lambda wo=wo, d=d: _tag_heats("Work Order", wo, d["heats"]))
		for i, op in enumerate(sorted(ops, key=lambda o: o.idx)):
			qty = d[op.qty_basis or "Total"]
			if qty <= 0:
				continue
			_run(lines, f"{op.operation} on {wo}",
				lambda wo=wo, op=op, qty=qty, d=d, i=i: _post_one(wo, op.operation, qty, when + timedelta(minutes=i), _ref(doc), d["heats"]))
	_status(doc, lines)


def _tag_heats(doctype, name, heats):
	if not heats:
		return
	current = frappe.db.get_value(doctype, name, "foundry_heats") or ""
	merged = sorted(set(filter(None, [h.strip() for h in current.split(",")])) | set(heats))
	frappe.db.set_value(doctype, name, "foundry_heats", ", ".join(merged), update_modified=False)


def _post_one(work_order, operation, qty, from_time, ref, heats):
	name = frappe.db.get_value("Job Card", {"work_order": work_order, "operation": operation, "docstatus": 0},
		"name", order_by="creation asc")
	if not name:
		done = frappe.db.exists("Job Card", {"work_order": work_order, "operation": operation, "docstatus": 1})
		return f"{OK} {operation} on {work_order} already complete" if done else f"{WARN} No open Job Card for {operation} on {work_order}"
	jc = frappe.get_doc("Job Card", name)
	remaining = flt(jc.for_quantity) - flt(jc.total_completed_qty)
	if remaining <= 0:
		return f"{OK} {jc.name} ({operation}) already has its full quantity"
	qty = min(flt(qty), remaining)
	jc.append("time_logs", {
		"from_time": from_time,
		"to_time": from_time + timedelta(minutes=1),
		"time_in_mins": 1,
		"completed_qty": qty,
		"foundry_ref": ref,
	})
	if heats:
		have = set(filter(None, [h.strip() for h in (jc.get("foundry_heats") or "").split(",")]))
		jc.foundry_heats = ", ".join(sorted(have | set(heats)))
	jc.flags.ignore_permissions = True
	jc.save()
	msg = f"{OK} {jc.name} ({operation}): +{qty:g}, total {flt(jc.total_completed_qty):g} of {flt(jc.for_quantity):g}"
	if cint(get_settings().submit_completed_job_cards) and flt(jc.total_completed_qty) >= flt(jc.for_quantity):
		jc.submit()
		msg += ", submitted"
	return msg


def remove_job_card_logs(doc):
	ref, lines = _ref(doc), []
	for jc_name in frappe.get_all("Job Card Time Log", filters={"foundry_ref": ref}, pluck="parent", distinct=True):
		jc = frappe.get_doc("Job Card", jc_name)
		if jc.docstatus != 0:
			lines.append(f"{WARN} {jc.name} is already submitted, cancel it manually to reverse")
			continue
		jc.time_logs = [t for t in jc.time_logs if t.foundry_ref != ref]
		jc.flags.ignore_permissions = True
		jc.save()
		lines.append(f"{OK} Removed quantity from {jc.name}")
	return lines


# ---------------------------------------------------------------- stock
def _stock_entry(doc, purpose, item_code, qty, s_warehouse=None, t_warehouse=None, rows=None):
	settings = get_settings()
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = purpose
	se.purpose = purpose
	se.company = settings.company or frappe.defaults.get_user_default("Company")
	se.posting_date = doc.posting_date
	se.set_posting_time = 1
	se.foundry_reference_doctype = doc.doctype
	se.foundry_reference_name = doc.name
	for r in rows or [dict(item_code=item_code, qty=qty)]:
		se.append("items", {
			"item_code": r["item_code"],
			"qty": r["qty"],
			"s_warehouse": s_warehouse,
			"t_warehouse": t_warehouse,
			"allow_zero_valuation_rate": 1 if t_warehouse and not s_warehouse else 0,
		})
	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	return se.name


def post_heat_charge(doc):
	s = get_settings()
	if not cint(s.post_heat_charge) or doc.get("charge_entry"):
		return
	lines = []

	def go():
		if not s.rm_warehouse:
			return f"{WARN} Set the Raw Material warehouse in Foundry Settings"
		rows = [dict(item_code=r.item_code, qty=r.qty_kg) for r in doc.charge if flt(r.qty_kg)]
		name = _stock_entry(doc, "Material Issue", None, None, s_warehouse=s.rm_warehouse, rows=rows)
		doc.db_set("charge_entry", name, update_modified=False)
		return f"{OK} Charge issued from stock: {name}"

	_run(lines, "Charge issue", go)
	_status(doc, lines)


def receive_return_metal(doc):
	s = get_settings()
	if not cint(s.post_return_metal) or not flt(doc.return_metal_kg) or doc.get("return_metal_entry"):
		return
	lines = [doc.erp_posting_status] if doc.erp_posting_status else []

	def go():
		if not (s.return_metal_item and s.scrap_warehouse):
			return f"{WARN} Set Return Metal Item and Return Metal Yard in Foundry Settings"
		name = _stock_entry(doc, "Material Receipt", s.return_metal_item, doc.return_metal_kg, t_warehouse=s.scrap_warehouse)
		doc.db_set("return_metal_entry", name, update_modified=False)
		return f"{OK} Return metal {flt(doc.return_metal_kg):g} kg received: {name}"

	_run(lines, "Return metal", go)
	doc.db_set("erp_posting_status", "\n".join(lines), update_modified=False)


def receive_rejected_castings(doc):
	s = get_settings()
	if not cint(s.post_rejection_to_scrap) or not flt(doc.total_kg) or doc.get("return_metal_entry"):
		return
	lines = []

	def go():
		if not (s.return_metal_item and s.scrap_warehouse):
			return f"{WARN} Set Return Metal Item and Return Metal Yard in Foundry Settings"
		name = _stock_entry(doc, "Material Receipt", s.return_metal_item, doc.total_kg, t_warehouse=s.scrap_warehouse)
		doc.db_set("return_metal_entry", name, update_modified=False)
		return f"{OK} Rejected castings {flt(doc.total_kg):g} kg to the return metal yard: {name}"

	_run(lines, "Rejected castings to yard", go)
	_status(doc, lines)


def cancel_linked_stock_entries(doc):
	for se in frappe.get_all("Stock Entry", filters={"foundry_reference_doctype": doc.doctype,
			"foundry_reference_name": doc.name, "docstatus": ["<", 2]}, fields=["name", "docstatus"]):
		entry = frappe.get_doc("Stock Entry", se.name)
		entry.flags.ignore_permissions = True
		if se.docstatus == 1:
			entry.cancel()
		else:
			entry.delete()


def make_manufacture_entries(doc):
	if not cint(get_settings().draft_manufacture_entry):
		return
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

	per_wo = {}
	for r in doc.items:
		if r.work_order and cint(r.ok_qty):
			per_wo[r.work_order] = per_wo.get(r.work_order, 0) + cint(r.ok_qty)
	lines, made = (doc.erp_posting_status or "").splitlines(), []

	for wo, qty in per_wo.items():
		if frappe.db.exists("Stock Entry", {"foundry_reference_doctype": doc.doctype, "foundry_reference_name": doc.name,
				"work_order": wo, "docstatus": ["<", 2]}):
			continue

		def go(wo=wo, qty=qty):
			se = frappe.get_doc(make_stock_entry(wo, "Manufacture", qty))
			se.foundry_reference_doctype = doc.doctype
			se.foundry_reference_name = doc.name
			se.flags.ignore_permissions = True
			se.insert()
			made.append(se.name)
			return f"{OK} Draft Manufacture entry {se.name} for {qty} on {wo}, for the storekeeper to submit"
		_run(lines, f"Manufacture entry for {wo}", go)
	if made:
		doc.db_set("manufacture_entries", ", ".join(made), update_modified=False)
	_status(doc, lines)


# ---------------------------------------------------------------- rejection report
def make_rejection_report(doc, stage, rows, produced=0):
	if not rows or not cint(get_settings().auto_rejection_report):
		return
	if frappe.db.exists("Rejection Report", {"reference_doctype": doc.doctype, "reference_name": doc.name, "docstatus": ["<", 2]}):
		return
	lines = (doc.erp_posting_status or "").splitlines()

	def go():
		rr = frappe.new_doc("Rejection Report")
		rr.posting_date = doc.posting_date
		rr.stage = stage
		rr.reference_doctype = doc.doctype
		rr.reference_name = doc.name
		rr.produced_nos = produced
		for r in rows:
			if not r.get("unit_weight") and r.get("item_code"):
				r["unit_weight"] = frappe.db.get_value("Item", r["item_code"], "casting_book_weight")
			rr.append("items", r)
		rr.flags.ignore_mandatory = True
		rr.flags.ignore_permissions = True
		rr.insert()
		doc.db_set("rejection_report", rr.name, update_modified=False)
		missing = " (fill in the missing reasons)" if any(not r.get("reason") for r in rows) else ""
		return f"{OK} Draft Rejection Report {rr.name}{missing}"

	_run(lines, "Rejection Report", go)
	_status(doc, lines)


# ---------------------------------------------------------------- aggregates
def update_heat_yield(heat):
	poured = frappe.db.sql("""select coalesce(sum(i.nos),0), coalesce(sum(i.weight_kg),0)
		from `tabProduction Entry Item` i join `tabProduction Entry` p on p.name = i.parent
		where p.docstatus = 1 and i.heat = %s""", heat)[0]
	rejected = frappe.db.sql("""select coalesce(sum(i.qty_nos),0), coalesce(sum(i.weight_kg),0)
		from `tabRejection Item` i join `tabRejection Report` r on r.name = i.parent
		where r.docstatus = 1 and i.heat = %s""", heat)[0]
	charge = flt(frappe.db.get_value("Furnace Heat", heat, "total_charge_kg"))
	good = flt(poured[1]) - flt(rejected[1])
	frappe.db.set_value("Furnace Heat", heat, {
		"poured_nos": cint(poured[0]), "poured_kg": flt(poured[1]),
		"rejected_nos": cint(rejected[0]), "rejected_kg": flt(rejected[1]),
		"good_kg": good, "yield_pct": good / charge * 100 if charge else 0,
	}, update_modified=False)


def update_pattern(pattern):
	used = frappe.db.sql("""select coalesce(sum(i.nos),0) from `tabProduction Entry Item` i
		join `tabProduction Entry` p on p.name = i.parent where p.docstatus = 1 and i.pattern = %s""", pattern)[0][0]
	required = cint(frappe.db.get_value("Pattern", pattern, "castings_required"))
	frappe.db.set_value("Pattern", pattern, {"shots_used": cint(used),
		"castings_balance": max(required - cint(used), 0) if required else 0}, update_modified=False)


def refresh_heats_and_patterns(doc):
	for heat in {r.heat for r in doc.items if r.get("heat")}:
		update_heat_yield(heat)
	for pattern in {r.pattern for r in doc.items if r.get("pattern")}:
		update_pattern(pattern)


def undo_automation(doc):
	lines = remove_job_card_logs(doc)
	cancel_linked_stock_entries(doc)
	for rr in frappe.get_all("Rejection Report", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}, fields=["name", "docstatus"]):
		if rr.docstatus == 0:
			frappe.delete_doc("Rejection Report", rr.name, ignore_permissions=True)
			lines.append(f"{OK} Deleted draft {rr.name}")
		elif rr.docstatus == 1:
			lines.append(f"{WARN} {rr.name} is submitted, cancel it if needed")
	if lines:
		frappe.msgprint("<br>".join(lines), title=_("Reversed postings"))
