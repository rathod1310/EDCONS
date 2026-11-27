# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

DEFECTS = {"shrinkage": "Shrinkage", "cold_shut": "Cold Shut", "sandfall": "Sandfall", "mismatch": "Mismatch", "core": "Core", "keyhole_sand": "Key Hole Sand", "fitment_rocking": "Fitment / Rocking", "frame_height": "Frame Height", "other_defects": "Other"}

class VisualInspection(Document):
	def validate(self):
		for row in self.items:
			auto.validate_work_order(row.work_order, row.item_code, row.idx)
			row.total_rejected = sum(cint(row.get(f)) for f in DEFECTS)
			if row.total_rejected > cint(row.qty_checked):
				frappe.throw(_("Row {0}: rejected ({1}) is more than checked ({2})").format(row.idx, row.total_rejected, row.qty_checked))
			row.ok_qty = cint(row.qty_checked) - row.total_rejected
		self.total_checked = sum(cint(r.qty_checked) for r in self.items)
		self.total_rejected = sum(cint(r.total_rejected) for r in self.items)
		self.total_ok = self.total_checked - self.total_rejected

	def on_submit(self):
		self.run_automation()

	def run_automation(self):
		auto.post_job_cards(self, total_field="qty_checked", good_field="ok_qty")
		rows = []
		for r in self.items:
			for field, reason in DEFECTS.items():
				if cint(r.get(field)):
					rows.append(dict(item_code=r.item_code, work_order=r.work_order, heat=r.heat,
					                 reason=reason, qty_nos=r.get(field)))
		auto.make_rejection_report(self, "Inspection", rows, produced=self.total_checked)
		auto.make_manufacture_entries(self)

	def on_cancel(self):
		auto.undo_automation(self)
