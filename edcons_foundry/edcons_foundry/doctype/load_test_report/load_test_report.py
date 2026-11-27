# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from edcons_foundry import automation as auto

class LoadTestReport(Document):
	def validate(self):
		results = []
		for row in self.items:
			if not flt(row.applied_load_kn):
				row.result = ""
				continue
			ok = flt(row.applied_load_kn) >= flt(row.required_load_kn)
			if flt(row.allowed_set_mm):
				ok = ok and flt(row.permanent_set_mm) <= flt(row.allowed_set_mm)
			row.result = "Pass" if ok else "Fail"
			results.append(row.result)
		self.overall_result = ("Fail" if "Fail" in results else "Pass") if results else ""

	def before_submit(self):
		if any(not r.result for r in self.items):
			frappe.throw(_("Enter the applied load for every row before submitting"))
