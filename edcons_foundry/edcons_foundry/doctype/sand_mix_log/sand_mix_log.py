# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class SandMixLog(Document):
	def validate(self):
		limits = auto.get_sand_limits(self.mould_type)
		bad = 0
		for row in self.batches:
			fails = auto.check_sand_row(row, limits)
			row.out_of_spec = ", ".join(fails)
			row.result = "Out of Spec" if fails else ("OK" if auto.sand_row_has_values(row) else "")
			bad += 1 if fails else 0
		self.batch_count = len(self.batches)
		self.out_of_spec_count = bad
		self.status = "Out of Spec" if bad else "OK"
