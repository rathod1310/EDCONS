# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class FinishingLog(Document):
	def validate(self):
		tol = flt(auto.get_settings().weight_tolerance_pct) or 3
		alerts = 0
		for row in self.items:
			auto.validate_work_order(row.work_order, row.item_code, row.idx)
			weights = auto.parse_weights(row.sample_weights)
			if weights:
				row.actual_weight = sum(weights) / len(weights)
			if flt(row.actual_weight) and flt(row.book_weight):
				row.weight_dev_pct = (flt(row.actual_weight) - flt(row.book_weight)) / flt(row.book_weight) * 100
				row.weight_flag = "Overweight" if row.weight_dev_pct > tol else ("Underweight" if row.weight_dev_pct < -tol else "OK")
			else:
				row.weight_dev_pct, row.weight_flag = 0, ""
			alerts += 1 if row.weight_flag in ("Overweight", "Underweight") else 0
			row.finished_kg = cint(row.finished_nos) * (flt(row.actual_weight) or flt(row.book_weight))
		self.total_finished_nos = sum(cint(r.finished_nos) for r in self.items)
		self.total_rejected_nos = sum(cint(r.rejected_nos) for r in self.items)
		self.total_finished_kg = sum(flt(r.finished_kg) for r in self.items)
		self.weight_alerts = alerts

	def on_submit(self):
		self.run_automation()

	def run_automation(self):
		for r in self.items:
			r.total_nos = cint(r.finished_nos) + cint(r.rejected_nos)
		auto.post_job_cards(self, total_field="total_nos", good_field="finished_nos")
		auto.make_rejection_report(self, "Finishing", [
			dict(item_code=r.item_code, work_order=r.work_order, heat=r.heat, moulder=r.worker,
			     reason=r.rejection_reason, qty_nos=r.rejected_nos, unit_weight=r.book_weight)
			for r in self.items if cint(r.rejected_nos)],
			produced=self.total_finished_nos + self.total_rejected_nos)

	def on_cancel(self):
		auto.undo_automation(self)
