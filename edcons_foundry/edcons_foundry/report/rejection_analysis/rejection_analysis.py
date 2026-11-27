import frappe
from frappe import _
from frappe.utils import flt

GROUPS = {"Reason": "i.reason", "Stage": "r.stage", "Item": "i.item_code", "Moulder": "i.moulder", "Heat": "i.heat"}


def execute(filters=None):
	filters = filters or {}
	group = filters.get("group_by") or "Reason"
	key = GROUPS[group]
	args = {"from": filters.get("from_date"), "to": filters.get("to_date"), "stage": filters.get("stage")}
	stage_cond = "and r.stage = %(stage)s" if filters.get("stage") else ""
	rows = frappe.db.sql(f"""select {key} as grp, sum(i.qty_nos) as qty, sum(i.weight_kg) as kg, count(distinct r.name) as reports
		from `tabRejection Item` i join `tabRejection Report` r on r.name = i.parent
		where r.docstatus = 1 and r.posting_date between %(from)s and %(to)s {stage_cond}
		group by {key} order by qty desc""", args, as_dict=True)
	produced = {}
	if group in ("Item", "Moulder", "Heat"):
		pk = {"Item": "i.item_code", "Moulder": "i.moulder", "Heat": "i.heat"}[group]
		for p in frappe.db.sql(f"""select {pk} as grp, sum(i.nos) as nos from `tabProduction Entry Item` i
				join `tabProduction Entry` p on p.name = i.parent
				where p.docstatus = 1 and p.posting_date between %(from)s and %(to)s group by {pk}""", args, as_dict=True):
			produced[p.grp] = flt(p.nos)
	total = sum(flt(r.qty) for r in rows)
	running = 0
	for r in rows:
		running += flt(r.qty)
		r.share = flt(r.qty) / total * 100 if total else 0
		r.cumulative = running / total * 100 if total else 0
		r.produced = produced.get(r.grp)
		r.rejection_pct = flt(r.qty) / r.produced * 100 if r.produced else None
		r.grp = r.grp or _("(not set)")
	opts = {"Reason": "Rejection Reason", "Item": "Item", "Moulder": "Employee", "Heat": "Furnace Heat"}
	columns = [
		{"label": _(group), "fieldname": "grp", "fieldtype": "Link" if group in opts else "Data", "options": opts.get(group), "width": 180},
		{"label": _("Rejected Pcs"), "fieldname": "qty", "fieldtype": "Int", "width": 110},
		{"label": _("Rejected kg"), "fieldname": "kg", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("Share %"), "fieldname": "share", "fieldtype": "Percent", "width": 90},
		{"label": _("Cumulative %"), "fieldname": "cumulative", "fieldtype": "Percent", "width": 110},
		{"label": _("Produced Pcs"), "fieldname": "produced", "fieldtype": "Int", "width": 110},
		{"label": _("Rejection %"), "fieldname": "rejection_pct", "fieldtype": "Percent", "width": 100},
		{"label": _("Reports"), "fieldname": "reports", "fieldtype": "Int", "width": 80},
	]
	top = rows[:12]
	chart = {"data": {"labels": [str(r.grp) for r in top], "datasets": [{"name": _("Rejected Pcs"), "values": [flt(r.qty) for r in top]}]},
		"type": "bar", "colors": ["#D9822B"]} if rows else None
	return columns, rows, None, chart
