/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PartnerLedgerReport extends Component {
    static template = "account_invoicing_ext_mz.PartnerLedgerReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            partners: [],
            totals: {
                debit: 0.0,
                credit: 0.0,
                balance: 0.0
            },
            isLoading: true,
            error: null,
            expandedPartners: new Set(),
            currencySymbol: 'MT',
            filters: {
                date_from: this.getDefaultDateFrom(),
                date_to: this.getDefaultDateTo(),
                partner_ids: [],
                account_type: 'all', // all, receivable, payable
                posted_entries: true,
                company_id: null
            },
            unpostedWarning: false
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    getDefaultDateFrom() {
        const now = new Date();
        return new Date(now.getFullYear(), 0, 1).toISOString().split('T')[0];
    }

    getDefaultDateTo() {
        return new Date().toISOString().split('T')[0];
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('pt-MZ', { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric' 
        });
    }

    async loadReport() {
        try {
            this.state.isLoading = true;
            this.state.error = null;

            const result = await this.rpc("/web/dataset/call_kw/account.partner.ledger.report/get_partner_ledger_data", {
                model: "account.partner.ledger.report",
                method: "get_partner_ledger_data",
                args: [],
                kwargs: {
                    date_from: this.state.filters.date_from,
                    date_to: this.state.filters.date_to,
                    partner_ids: this.state.filters.partner_ids.length > 0 ? this.state.filters.partner_ids : null,
                    account_type: this.state.filters.account_type,
                    posted_entries: this.state.filters.posted_entries,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.partners = result.partners || [];
            this.state.totals = result.totals || { debit: 0.0, credit: 0.0, balance: 0.0 };
            this.state.currencySymbol = result.currency_symbol || 'MT';
            this.state.unpostedWarning = result.unposted_warning || false;

        } catch (error) {
            console.error("Error loading partner ledger:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    togglePartner(partnerId) {
        if (this.state.expandedPartners.has(partnerId)) {
            this.state.expandedPartners.delete(partnerId);
        } else {
            this.state.expandedPartners.add(partnerId);
        }
    }

    isExpanded(partnerId) {
        return this.state.expandedPartners.has(partnerId);
    }

    formatCurrency(amount) {
        if (amount === undefined || amount === null) return '0,00';
        return new Intl.NumberFormat('pt-MZ', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(Math.abs(amount));
    }

    async onDateFromChange(ev) {
        this.state.filters.date_from = ev.target.value;
        await this.loadReport();
    }

    async onDateToChange(ev) {
        this.state.filters.date_to = ev.target.value;
        await this.loadReport();
    }

    async onAccountTypeChange(type) {
        this.state.filters.account_type = type;
        await this.loadReport();
    }

    async onPostedEntriesToggle() {
        this.state.filters.posted_entries = !this.state.filters.posted_entries;
        await this.loadReport();
    }

    async onPartnerFilterClick() {
        // In real implementation, show partner selection dialog
        console.log("Partner filter clicked");
    }

    async exportToPDF() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'qweb-pdf',
                report_name: 'account_invoicing_ext_mz.partner_ledger_report',
                report_file: 'account_invoicing_ext_mz.partner_ledger_report',
                data: {
                    partners: this.state.partners,
                    totals: this.state.totals,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to PDF:", error);
        }
    }

    async exportToXLSX() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'xlsx',
                report_name: 'account_invoicing_ext_mz.partner_ledger_xlsx',
                report_file: 'account_invoicing_ext_mz.partner_ledger_xlsx',
                data: {
                    partners: this.state.partners,
                    totals: this.state.totals,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    showPartnerDetails(partner) {
        // Show partner details in a dialog
        console.log("Show details for:", partner);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }
}

registry.category("actions").add("account_partner_ledger_report", PartnerLedgerReport);