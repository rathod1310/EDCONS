# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class RejectionReport(Document):
	def validate(self):
		for row in self.items:
			row.weight_kg = cint(row.qty_nos) * flt(row.unit_weight)
		self.total_nos = sum(cint(r.qty_nos) for r in self.items)
		self.total_kg = sum(flt(r.weight_kg) for r in self.items)
		self.rejection_pct = self.total_nos / cint(self.produced_nos) * 100 if cint(self.produced_nos) else 0

	def on_submit(self):
		self.run_automation()

	def run_automation(self):
		auto.receive_rejected_castings(self)
		for heat in {r.heat for r in self.items if r.heat}:
			auto.update_heat_yield(heat)

	def on_cancel(self):
		auto.cancel_linked_stock_entries(self)
		for heat in {r.heat for r in self.items if r.heat}:
			auto.update_heat_yield(heat)
