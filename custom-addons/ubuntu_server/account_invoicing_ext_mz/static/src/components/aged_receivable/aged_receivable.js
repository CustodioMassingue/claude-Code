/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AgedReceivableReport extends Component {
    static template = "account_invoicing_ext_mz.AgedReceivableReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            partners: [],
            totals: {
                invoice_date: 0.0,
                at_date: 0.0,
                period_1: 0.0,
                period_2: 0.0,
                period_3: 0.0,
                period_4: 0.0,
                older: 0.0,
                total: 0.0
            },
            periods: [],
            isLoading: true,
            error: null,
            expandedPartners: new Set(),
            currencySymbol: 'MT',
            filters: {
                as_of_date: new Date().toISOString().split('T')[0],
                account_type: 'receivable',
                partner_ids: [],
                period_length: 30,
                posted_entries: true,
                company_id: null,
                based_on: 'due_date' // due_date or invoice_date
            },
            unpostedWarning: false
        });

        onWillStart(async () => {
            await this.loadReport();
        });
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

            const result = await this.rpc("/web/dataset/call_kw/account.aged.receivable.report/get_aged_receivable_data", {
                model: "account.aged.receivable.report",
                method: "get_aged_receivable_data",
                args: [],
                kwargs: {
                    as_of_date: this.state.filters.as_of_date,
                    account_type: this.state.filters.account_type,
                    partner_ids: this.state.filters.partner_ids.length > 0 ? this.state.filters.partner_ids : null,
                    period_length: this.state.filters.period_length,
                    posted_entries: this.state.filters.posted_entries,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.partners = result.partners || [];
            this.state.totals = result.totals || {
                invoice_date: 0.0,
                at_date: 0.0,
                period_1: 0.0,
                period_2: 0.0,
                period_3: 0.0,
                period_4: 0.0,
                older: 0.0,
                total: 0.0
            };
            this.state.periods = result.periods || [];
            this.state.currencySymbol = result.currency_symbol || 'MT';
            this.state.unpostedWarning = result.unposted_warning || false;

        } catch (error) {
            console.error("Error loading aged receivable:", error);
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

    async onAsOfDateChange(ev) {
        this.state.filters.as_of_date = ev.target.value;
        await this.loadReport();
    }

    async onAccountTypeChange(type) {
        this.state.filters.account_type = type;
        await this.loadReport();
    }

    async onPartnerFilterClick() {
        // In real implementation, show partner selection dialog
        console.log("Partner filter clicked");
    }

    async onPeriodLengthChange(length) {
        this.state.filters.period_length = length;
        await this.loadReport();
    }

    async onBasedOnChange(basedOn) {
        this.state.filters.based_on = basedOn;
        await this.loadReport();
    }

    async exportToPDF() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'qweb-pdf',
                report_name: 'account_invoicing_ext_mz.aged_receivable_report',
                report_file: 'account_invoicing_ext_mz.aged_receivable_report',
                data: {
                    partners: this.state.partners,
                    totals: this.state.totals,
                    periods: this.state.periods,
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
                report_name: 'account_invoicing_ext_mz.aged_receivable_xlsx',
                report_file: 'account_invoicing_ext_mz.aged_receivable_xlsx',
                data: {
                    partners: this.state.partners,
                    totals: this.state.totals,
                    periods: this.state.periods,
                    filters: this.state.filters,
                    currency_symbol: this.state.currencySymbol
                },
                context: this.user.context,
            });
        } catch (error) {
            console.error("Error exporting to XLSX:", error);
        }
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }
}

registry.category("actions").add("account_aged_receivable_report", AgedReceivableReport);