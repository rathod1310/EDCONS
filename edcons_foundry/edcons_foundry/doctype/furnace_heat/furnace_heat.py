# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class FurnaceHeat(Document):
	def validate(self):
		self.set_lining()
		self.calculate()

	def set_lining(self):
		if not self.furnace:
			return
		furnace = frappe.db.get_value("Furnace", self.furnace, ["current_lining_no", "heats_on_lining", "melt_type"], as_dict=True)
		if not self.lining_no:
			self.lining_no = furnace.current_lining_no
		if not self.lining_heat_no:
			self.lining_heat_no = cint(furnace.heats_on_lining) + 1
		if not self.melt_type:
			self.melt_type = furnace.melt_type

	def calculate(self):
		total = cost = ret = 0
		for row in self.charge:
			row.amount = flt(row.qty_kg) * flt(row.rate)
			if row.charge_type == "Coke":
				continue
			total += flt(row.qty_kg)
			cost += row.amount
			if row.charge_type == "Return Metal":
				ret += flt(row.qty_kg)
		self.total_charge_kg = total
		self.return_metal_kg = ret
		self.charge_cost = cost
		self.cost_per_kg = cost / total if total else 0
		if self.kwh_end and flt(self.kwh_end) < flt(self.kwh_start):
			frappe.throw(_("Meter End cannot be less than Meter Start"))
		self.kwh_consumed = flt(self.kwh_end) - flt(self.kwh_start) if self.kwh_end else 0
		metal = flt(self.liquid_metal_kg) or total
		self.kwh_per_tonne = flt(self.kwh_consumed) / (metal / 1000.0) if metal and self.kwh_consumed else 0
		self.ce_pct = flt(self.c_pct) + (flt(self.si_pct) + flt(self.p_pct)) / 3.0 if self.c_pct else 0
		coke = flt(self.coke_kg) or sum(flt(r.qty_kg) for r in self.charge if r.charge_type == "Coke")
		self.coke_ratio = total / coke if coke else 0

	def on_submit(self):
		current = cint(frappe.db.get_value("Furnace", self.furnace, "heats_on_lining"))
		if cint(self.lining_heat_no) > current:
			frappe.db.set_value("Furnace", self.furnace, "heats_on_lining", self.lining_heat_no)
		self.run_automation()

	def run_automation(self):
		auto.post_heat_charge(self)
		auto.update_heat_yield(self.name)

	def on_cancel(self):
		auto.cancel_linked_stock_entries(self)
