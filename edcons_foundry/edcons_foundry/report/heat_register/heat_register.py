import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	cond = {"docstatus": 1, "posting_date": ["between", [filters.get("from_date"), filters.get("to_date")]]}
	if filters.get("furnace"):
		cond["furnace"] = filters["furnace"]
	if filters.get("melt_type"):
		cond["melt_type"] = filters["melt_type"]
	data = frappe.get_all("Furnace Heat", filters=cond, order_by="posting_date, name", fields=[
		"name", "posting_date", "shift", "furnace", "lining_no", "lining_heat_no", "grade", "total_charge_kg",
		"return_metal_kg", "kwh_consumed", "kwh_per_tonne", "ce_pct", "tapping_temp", "poured_nos", "poured_kg",
		"rejected_kg", "good_kg", "yield_pct", "cost_per_kg", "chemistry_status"])
	columns = [
		{"label": _("Heat"), "fieldname": "name", "fieldtype": "Link", "options": "Furnace Heat", "width": 140},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Shift"), "fieldname": "shift", "width": 60},
		{"label": _("Furnace"), "fieldname": "furnace", "fieldtype": "Link", "options": "Furnace", "width": 110},
		{"label": _("Lining / Heat"), "fieldname": "lining", "width": 90},
		{"label": _("Grade"), "fieldname": "grade", "width": 80},
		{"label": _("Charge kg"), "fieldname": "total_charge_kg", "fieldtype": "Float", "precision": 0, "width": 95},
		{"label": _("Return kg"), "fieldname": "return_metal_kg", "fieldtype": "Float", "precision": 0, "width": 90},
		{"label": _("kWh"), "fieldname": "kwh_consumed", "fieldtype": "Float", "precision": 0, "width": 80},
		{"label": _("kWh/t"), "fieldname": "kwh_per_tonne", "fieldtype": "Float", "precision": 0, "width": 75},
		{"label": _("CE %"), "fieldname": "ce_pct", "fieldtype": "Float", "precision": 2, "width": 70},
		{"label": _("Tap °C"), "fieldname": "tapping_temp", "fieldtype": "Float", "precision": 0, "width": 70},
		{"label": _("Poured Nos"), "fieldname": "poured_nos", "fieldtype": "Int", "width": 85},
		{"label": _("Poured kg"), "fieldname": "poured_kg", "fieldtype": "Float", "precision": 0, "width": 90},
		{"label": _("Rejected kg"), "fieldname": "rejected_kg", "fieldtype": "Float", "precision": 0, "width": 90},
		{"label": _("Good kg"), "fieldname": "good_kg", "fieldtype": "Float", "precision": 0, "width": 85},
		{"label": _("Yield %"), "fieldname": "yield_pct", "fieldtype": "Percent", "width": 80},
		{"label": _("Cost/kg"), "fieldname": "cost_per_kg", "fieldtype": "Currency", "width": 85},
		{"label": _("Lab"), "fieldname": "chemistry_status", "width": 80},
	]
	for d in data:
		d.lining = f"{d.lining_no or ''} / {d.lining_heat_no or ''}"
	chart = None
	if data:
		chart = {"data": {"labels": [d.name for d in data], "datasets": [
			{"name": _("kWh/t"), "values": [flt(d.kwh_per_tonne) for d in data]},
			{"name": _("Yield %"), "values": [flt(d.yield_pct) for d in data]}]},
			"type": "line", "colors": ["#2F6FDE", "#D9822B"]}
	melt = sum(flt(d.total_charge_kg) for d in data)
	kwh = sum(flt(d.kwh_consumed) for d in data)
	good = sum(flt(d.good_kg) for d in data)
	summary = [
		{"label": _("Heats"), "value": len(data), "datatype": "Int"},
		{"label": _("Metal melted (kg)"), "value": melt, "datatype": "Float"},
		{"label": _("kWh per tonne"), "value": kwh / (melt / 1000) if melt else 0, "datatype": "Float"},
		{"label": _("Yield %"), "value": good / melt * 100 if melt else 0, "datatype": "Percent"},
	]
	return columns, data, None, chart, summary
