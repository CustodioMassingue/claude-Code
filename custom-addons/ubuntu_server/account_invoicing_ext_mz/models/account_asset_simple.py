from odoo import models, fields, _

class AccountAssetSimple(models.Model):
    _name = "account.asset.simple"
    _description = "Simple Asset (MZ)"
    _order = "acquisition_date desc, id desc"

    name = fields.Char(required=True)
    acquisition_date = fields.Date(required=True, default=fields.Date.context_today)
    original_value = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id.id)
    depreciation_months = fields.Integer(required=True, default=12)
    accumulated_depr = fields.Monetary(default=0.0)
    value_net = fields.Monetary(compute="_compute_value_net", store=True)
    expense_account_id = fields.Many2one("account.account", required=True, domain=[("internal_type","=","other")])
    asset_account_id = fields.Many2one("account.account", required=True, domain=[("internal_type","=","other")])
    journal_id = fields.Many2one("account.journal", required=True, domain=[("type","=","general")])
    state = fields.Selection([("open","Running"),("closed","Closed")], default="open")

    def action_post_month(self):
        for rec in self.filtered(lambda r: r.state == "open"):
            monthly = (rec.original_value / rec.depreciation_months) if rec.depreciation_months else 0.0
            if monthly <= 0:
                continue
            move = self.env["account.move"].create({
                "move_type": "entry",
                "date": fields.Date.today(),
                "journal_id": rec.journal_id.id,
                "line_ids": [
                    (0,0,{"name": _("Depreciation %s") % rec.name, "account_id": rec.expense_account_id.id, "debit": monthly, "credit": 0.0}),
                    (0,0,{"name": _("Depreciation %s") % rec.name, "account_id": rec.asset_account_id.id, "debit": 0.0, "credit": monthly}),
                ]
            })
            move.action_post()
            rec.accumulated_depr += monthly
            if rec.original_value - rec.accumulated_depr <= 0.0001:
                rec.state = "closed"

    def _compute_value_net(self):
        for rec in self:
            rec.value_net = rec.original_value - (rec.accumulated_depr or 0.0)
