/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TrialBalanceReport extends Component {
    static template = "account_invoicing_ext_mz.TrialBalanceReport";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        
        this.state = useState({
            accounts: [],
            totals: {
                initial_debit: 0,
                initial_credit: 0,
                period_debit: 0,
                period_credit: 0,
                end_debit: 0,
                end_credit: 0
            },
            isLoading: true,
            error: null,
            currencySymbol: 'MZN',
            searchQuery: '',
            filters: {
                date_from: null,
                date_to: this.getCurrentMonth(),
                journals: 'all',
                journal_ids: [],
                analytic: null,
                posted_entries: true,
                comparison: null,
                company_id: null
            },
            unpostedWarning: false
        });

        onWillStart(async () => {
            await this.loadReport();
        });
    }

    getCurrentMonth() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[date.getMonth()]} ${date.getFullYear()}`;
    }

    async loadReport() {
        try {
            this.state.isLoading = true;
            this.state.error = null;

            const result = await this.rpc("/web/dataset/call_kw/account.trial.balance.report/get_trial_balance_data", {
                model: "account.trial.balance.report",
                method: "get_trial_balance_data",
                args: [],
                kwargs: {
                    date_from: this.state.filters.date_from,
                    date_to: this.state.filters.date_to ? new Date(this.state.filters.date_to + '-01') : null,
                    journals: this.state.filters.journal_ids.length > 0 ? this.state.filters.journal_ids : null,
                    analytic: this.state.filters.analytic,
                    posted_entries: this.state.filters.posted_entries,
                    comparison: this.state.filters.comparison,
                    company_id: this.state.filters.company_id || this.user.context.allowed_company_ids[0]
                }
            });

            if (result.error) {
                throw new Error(result.error);
            }

            this.state.accounts = result.accounts || [];
            this.state.totals = result.totals || {
                initial_debit: 0,
                initial_credit: 0,
                period_debit: 0,
                period_credit: 0,
                end_debit: 0,
                end_credit: 0
            };
            this.state.currencySymbol = result.currency_symbol || 'MZN';
            this.state.unpostedWarning = result.unposted_warning || false;

        } catch (error) {
            console.error("Error loading trial balance:", error);
            this.state.error = error.message || "Failed to load report";
        } finally {
            this.state.isLoading = false;
        }
    }

    getFilteredAccounts() {
        if (!this.state.searchQuery) {
            return this.state.accounts;
        }
        
        const query = this.state.searchQuery.toLowerCase();
        return this.state.accounts.filter(account => 
            account.code.toLowerCase().includes(query) || 
            account.name.toLowerCase().includes(query)
        );
    }

    formatCurrency(amount) {
        if (amount === undefined || amount === null || amount === 0) return '';
        return new Intl.NumberFormat('pt-MZ', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(Math.abs(amount));
    }

    async onSearchChange(ev) {
        this.state.searchQuery = ev.target.value;
    }

    async onDateChange(ev) {
        const value = ev.target.value;
        if (value) {
            this.state.filters.date_to = value;
            await this.loadReport();
        }
    }

    async onComparisonClick() {
        // Show comparison options dialog
        console.log("Comparison filter clicked");
    }

    async onJournalFilterClick(filter) {
        if (filter === 'all') {
            this.state.filters.journals = 'all';
            this.state.filters.journal_ids = [];
        } else {
            // In real implementation, show journal selection dialog
            this.state.filters.journals = filter;
        }
        await this.loadReport();
    }

    async onAnalyticClick() {
        // Show analytic filter dialog
        console.log("Analytic filter clicked");
    }

    async onPostedEntriesToggle() {
        this.state.filters.posted_entries = !this.state.filters.posted_entries;
        await this.loadReport();
    }

    async exportToPDF() {
        try {
            await this.action.doAction({
                type: 'ir.actions.report',
                report_type: 'qweb-pdf',
                report_name: 'account_invoicing_ext_mz.trial_balance_report',
                report_file: 'account_invoicing_ext_mz.trial_balance_report',
                data: {
                    accounts: this.state.accounts,
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
                report_name: 'account_invoicing_ext_mz.trial_balance_xlsx',
                report_file: 'account_invoicing_ext_mz.trial_balance_xlsx',
                data: {
                    accounts: this.state.accounts,
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

    showAccountDetails(account) {
        // Show account details in a dialog
        console.log("Show details for:", account);
    }

    showSettings() {
        // Show report settings
        console.log("Show settings");
    }
}

registry.category("actions").add("account_trial_balance_report", TrialBalanceReport);