# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class ShotBlastLog(Document):
	def validate(self):
		for row in self.items:
			if cint(row.rejected_nos) > cint(row.nos):
				frappe.throw(_("Row {0}: rejected cannot be more than blasted").format(row.idx))
			auto.validate_work_order(row.work_order, row.item_code, row.idx)
			row.weight_kg = cint(row.nos) * flt(row.std_weight)
		self.total_nos = sum(cint(r.nos) for r in self.items)
		self.total_rejected_nos = sum(cint(r.rejected_nos) for r in self.items)
		self.total_kg = sum(flt(r.weight_kg) for r in self.items)
		if self.hour_meter_end:
			self.running_hours = flt(self.hour_meter_end) - flt(self.hour_meter_start)

	def on_submit(self):
		self.run_automation()

	def run_automation(self):
		for r in self.items:
			r.good_nos = cint(r.nos) - cint(r.rejected_nos)
		auto.post_job_cards(self, total_field="nos", good_field="good_nos")
		auto.make_rejection_report(self, "Shot Blasting", [
			dict(item_code=r.item_code, work_order=r.work_order, heat=r.heat, reason=r.rejection_reason,
			     qty_nos=r.rejected_nos, unit_weight=r.std_weight)
			for r in self.items if cint(r.rejected_nos)], produced=self.total_nos)

	def on_cancel(self):
		auto.undo_automation(self)
