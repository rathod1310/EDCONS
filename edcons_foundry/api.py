"""Whitelisted methods for the Shop Floor hub, Heat Traceability and next-step buttons."""
import frappe
from frappe import _
from frappe.utils import cint, flt, today

from edcons_foundry import automation as auto

LOG_DOCTYPES = ["Furnace Heat", "Sand Mix Log", "Production Entry", "Shot Blast Log", "Finishing Log",
	"Visual Inspection", "Load Test Report", "Rejection Report"]


def _sum(doctype, field, filters):
	return flt(frappe.db.get_value(doctype, filters, f"sum({field})") or 0)


@frappe.whitelist()
def get_hub_data():
	d = today()
	sub = {"posting_date": d, "docstatus": 1}
	heats = frappe.db.count("Furnace Heat", sub)
	melt = _sum("Furnace Heat", "total_charge_kg", sub)
	kwh = _sum("Furnace Heat", "kwh_consumed", sub)
	cast_nos = _sum("Production Entry", "total_nos", sub)
	cast_kg = _sum("Production Entry", "total_weight_kg", sub)
	rej = _sum("Rejection Report", "total_nos", sub)
	sand_bad = _sum("Sand Mix Log", "out_of_spec_count", {"posting_date": d, "docstatus": ["<", 2]})
	drafts = []
	for dt in LOG_DOCTYPES:
		for r in frappe.get_all(dt, filters={"docstatus": 0}, fields=["name", "posting_date", "modified", "owner"],
				order_by="modified desc", limit=10):
			r.doctype = dt
			r.mine = r.owner == frappe.session.user
			drafts.append(r)
	drafts.sort(key=lambda r: r.modified, reverse=True)
	recent_heats = frappe.get_all("Furnace Heat", filters={"docstatus": ["<", 2]},
		fields=["name", "posting_date", "shift", "furnace", "grade", "total_charge_kg", "kwh_per_tonne",
			"poured_nos", "yield_pct", "chemistry_status", "docstatus"],
		order_by="creation desc", limit=8)
	return {
		"kpis": {
			"heats": heats, "melt_kg": melt,
			"kwh_per_tonne": kwh / (melt / 1000.0) if melt else 0,
			"kwh_target": flt(auto.get_settings().kwh_target),
			"cast_nos": cast_nos, "cast_kg": cast_kg,
			"rejected": rej, "rejection_pct": rej / cast_nos * 100 if cast_nos else 0,
			"sand_out_of_spec": sand_bad,
			"weight_alerts": _sum("Finishing Log", "weight_alerts", {"posting_date": d, "docstatus": ["<", 2]}),
		},
		"drafts": drafts[:15],
		"recent_heats": recent_heats,
	}


def _rows(parent, child, fields, heat, extra_parent=()):
	pf = ", ".join(f"p.{f}" for f in ("name", "posting_date", "docstatus") + tuple(extra_parent))
	cf = ", ".join(f"i.{f}" for f in fields)
	return frappe.db.sql(f"""select {pf}, {cf} from `tab{child}` i join `tab{parent}` p on p.name = i.parent
		where i.heat = %s and p.docstatus < 2 order by p.posting_date, p.name, i.idx""", heat, as_dict=True)


@frappe.whitelist()
def trace_heat(heat):
	if not frappe.has_permission("Furnace Heat", "read", heat):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	h = frappe.get_doc("Furnace Heat", heat)
	production = _rows("Production Entry", "Production Entry Item",
		("moulder_name", "item_code", "item_name", "work_order", "nos", "rejected_nos", "weight_kg"), heat, ("shift",))
	work_orders = sorted({r.work_order for r in production if r.work_order})
	wo_info = frappe.get_all("Work Order", filters={"name": ["in", work_orders or ["-"]]},
		fields=["name", "production_item", "qty", "produced_qty", "status", "sales_order"])
	sales_orders = sorted({w.sales_order for w in wo_info if w.sales_order})
	dispatch = frappe.db.sql("""select distinct dn.name, dn.posting_date, dn.customer, dn.docstatus, dni.item_code, dni.qty
		from `tabDelivery Note Item` dni join `tabDelivery Note` dn on dn.name = dni.parent
		where dni.against_sales_order in %(so)s and dn.docstatus < 2
		and dni.item_code in %(items)s order by dn.posting_date""",
		{"so": sales_orders or ["-"], "items": [w.production_item for w in wo_info] or ["-"]}, as_dict=True)
	return {
		"heat": h.as_dict(),
		"production": production,
		"work_orders": wo_info,
		"job_cards": frappe.get_all("Job Card", filters={"work_order": ["in", work_orders or ["-"]]},
			fields=["name", "work_order", "operation", "for_quantity", "total_completed_qty", "status", "docstatus"],
			order_by="work_order, sequence_id, creation"),
		"shot_blast": _rows("Shot Blast Log", "Shot Blast Item", ("item_code", "work_order", "nos", "rejected_nos"), heat),
		"finishing": _rows("Finishing Log", "Finishing Log Item",
			("worker_name", "process", "item_code", "finished_nos", "rejected_nos", "actual_weight", "weight_flag"), heat),
		"inspection": _rows("Visual Inspection", "Visual Inspection Item", ("item_code", "qty_checked", "total_rejected", "ok_qty"), heat),
		"load_tests": _rows("Load Test Report", "Load Test Item", ("item_code", "standard", "required_load_kn", "applied_load_kn", "result"), heat),
		"rejections": _rows("Rejection Report", "Rejection Item", ("item_code", "reason", "qty_nos", "weight_kg"), heat, ("stage",)),
		"dispatch": dispatch,
	}


# ---------------------------------------------------------------- next step mapping
def _copy(src, keys):
	return {k: src.get(k) for k in keys if src.get(k) not in (None, "")}


@frappe.whitelist()
def make_next(source_doctype, source_name, target_doctype):
	src = frappe.get_doc(source_doctype, source_name)
	src.check_permission("read")
	t = frappe.new_doc(target_doctype)
	if t.meta.has_field("posting_date"):
		t.posting_date = today()
	if t.meta.has_field("shift") and src.get("shift"):
		t.shift = src.shift

	def items_from(fn):
		for r in src.items:
			row = fn(r)
			if row:
				t.append("items", row)

	key = (source_doctype, target_doctype)
	if source_doctype == "Furnace Heat":
		if target_doctype == "Production Entry":
			t.melt_type = src.melt_type
			t.append("items", {"heat": src.name})
		elif target_doctype == "Load Test Report":
			t.append("items", {"heat": src.name})
	elif key == ("Production Entry", "Shot Blast Log"):
		items_from(lambda r: cint(r.good_nos) and dict(_copy(r, ("item_code", "work_order", "heat")), nos=r.good_nos))
	elif key == ("Shot Blast Log", "Finishing Log"):
		items_from(lambda r: dict(_copy(r, ("item_code", "work_order", "heat")),
			received_nos=cint(r.nos) - cint(r.rejected_nos), finished_nos=cint(r.nos) - cint(r.rejected_nos)))
	elif key == ("Production Entry", "Finishing Log"):
		items_from(lambda r: cint(r.good_nos) and dict(_copy(r, ("item_code", "work_order", "heat")),
			received_nos=r.good_nos, finished_nos=r.good_nos))
	elif key == ("Finishing Log", "Visual Inspection"):
		items_from(lambda r: cint(r.finished_nos) and dict(_copy(r, ("item_code", "work_order", "heat")), qty_checked=r.finished_nos))
	elif key == ("Visual Inspection", "Load Test Report"):
		t.customer = src.customer
		items_from(lambda r: cint(r.ok_qty) and _copy(r, ("item_code", "heat")))
	elif key == ("Work Order", "Production Entry"):
		t.append("items", {"item_code": src.production_item, "work_order": src.name})
	else:
		frappe.throw(_("Cannot make {0} from {1}").format(target_doctype, source_doctype))
	return t.as_dict()


@frappe.whitelist()
def retry_posting(doctype, name):
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted documents can be posted"))
	auto.remove_job_card_logs(doc)
	doc.run_automation()
	return frappe.db.get_value(doctype, name, "erp_posting_status")


@frappe.whitelist()
def start_new_lining(furnace):
	frappe.has_permission("Furnace", "write", furnace, throw=True)
	f = frappe.get_doc("Furnace", furnace)
	f.current_lining_no = cint(f.current_lining_no) + 1
	f.heats_on_lining = 0
	f.save()
	return f.current_lining_no
