# Copyright (c) 2026, Edcons (MKS) Castings and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import cint, flt

class Pattern(Document):
	def validate(self):
		self.balance_qty = cint(self.receiving_qty) - cint(self.return_qty)
		self.castings_balance = max(cint(self.castings_required) - cint(self.shots_used), 0) if self.castings_required else 0
		if self.return_qty and cint(self.return_qty) >= cint(self.receiving_qty) and self.status == "Active":
			self.status = "Returned"
