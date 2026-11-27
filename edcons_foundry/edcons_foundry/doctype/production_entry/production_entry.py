# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class ProductionEntry(Document):
	def validate(self):
		total = weight = rej = 0
		heats = []
		for row in self.items:
			if cint(row.rejected_nos) > cint(row.nos):
				frappe.throw(_("Row {0}: rejected cannot be more than cast").format(row.idx))
			auto.validate_heat(row.heat, row.idx)
			auto.validate_work_order(row.work_order, row.item_code, row.idx)
			row.weight_kg = cint(row.nos) * flt(row.book_weight)
			row.good_nos = cint(row.nos) - cint(row.rejected_nos)
			total += cint(row.nos)
			rej += cint(row.rejected_nos)
			weight += row.weight_kg
			if row.heat and row.heat not in heats:
				heats.append(row.heat)
		for p in self.pouring:
			p.pouring_velocity = flt(p.good_casting_wt) / flt(p.pouring_time_sec) if flt(p.pouring_time_sec) else 0
		self.total_nos, self.total_rejected_nos = total, rej
		self.total_good_nos = total - rej
		self.total_weight_kg = weight
		self.heats = ", ".join(heats)

	def on_submit(self):
		self.run_automation()

	def run_automation(self):
		auto.post_job_cards(self, total_field="nos", good_field="good_nos")
		auto.receive_return_metal(self)
		auto.make_rejection_report(self, "Moulding", [
			dict(item_code=r.item_code, work_order=r.work_order, heat=r.heat, moulder=r.moulder,
			     reason=r.rejection_reason, qty_nos=r.rejected_nos, unit_weight=r.book_weight)
			for r in self.items if cint(r.rejected_nos)], produced=self.total_nos)
		auto.refresh_heats_and_patterns(self)

	def on_cancel(self):
		auto.undo_automation(self)
		auto.refresh_heats_and_patterns(self)
