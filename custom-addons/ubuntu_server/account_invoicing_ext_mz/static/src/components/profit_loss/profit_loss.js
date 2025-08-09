/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ProfitLossReport extends Component {
    static template = "account_invoicing_ext_mz.ProfitLossReport";
    static props = {
        action: { type: Object, optional: true },
    };
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.user = useService("user");
        
        this.state = useState({
            loading: true,
            error: null,
            data: null,
            expandedLines: new Set(),
            date_from: this.getDefaultDateFrom(),
            date_to: this.getDefaultDateTo(),
            comparison: false,
            comparisonMode: 'none', // none, previous, year, specific
            comparisonDateFrom: null,
            comparisonDateTo: null,
            periodOrder: 'descending',
            dateFilter: 'year', // today, month, quarter, year, specific
            journals: [],
            allJournals: true,
            selectedJournalsCount: 0,
            showAnalytic: false,
            analyticAccounts: [],
            analyticPlans: [],
            showPartners: false,
            partners: [],
            onlyPosted: true,
            hasUnposted: false,
            includeDraft: false,
            includeSimulations: false,
            hideZeroBalances: false,
            splitHorizontally: false,
            showBudget: false,
            filters: {
                date_from: this.getDefaultDateFrom(),
                date_to: this.getDefaultDateTo(),
                journals: [],
                comparison: false,
            }
        });
        
        onWillStart(async () => {
            await this.loadJournals();
            await this.loadProfitLossData();
        });
        
        onMounted(() => {
            this.setupDatePicker();
        });
    }
    
    getDefaultDateFrom() {
        const today = new Date();
        return new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0];
    }
    
    getDefaultDateTo() {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }
    
    getDateRangeLabel() {
        const from = new Date(this.state.date_from);
        const to = new Date(this.state.date_to);
        if (from.getFullYear() === to.getFullYear()) {
            return from.getFullYear().toString();
        }
        return `${from.getFullYear()} - ${to.getFullYear()}`;
    }
    
    async loadJournals() {
        try {
            const journals = await this.orm.searchRead(
                "account.journal",
                [["company_id", "=", this.user.context.company_id || false]],
                ["id", "name", "code", "type"]
            );
            this.state.journals = journals;
        } catch (error) {
            console.error("Failed to load journals:", error);
        }
    }
    
    async loadProfitLossData() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const result = await this.rpc("/account/profit_loss/data", {
                date_from: this.state.date_from,
                date_to: this.state.date_to,
                journals: this.state.allJournals ? null : this.state.filters.journals,
                company_id: this.user.context.company_id || false,
                comparison: this.state.comparison,
                comparison_date_from: this.state.comparisonDateFrom,
                comparison_date_to: this.state.comparisonDateTo,
                comparison_mode: this.state.comparisonMode,
                only_posted: this.state.onlyPosted,
                include_draft: this.state.includeDraft,
                include_simulations: this.state.includeSimulations,
                hide_zero: this.state.hideZeroBalances,
                analytic_accounts: this.state.analyticAccounts,
                analytic_plans: this.state.analyticPlans,
                partners: this.state.showPartners ? this.state.partners : null,
            });
            
            if (result.success) {
                this.state.data = result.data;
                this.state.hasUnposted = result.data.has_unposted || false;
                
                // Auto-expand first level
                if (result.data.lines) {
                    result.data.lines.forEach(line => {
                        if (line.level === 0 && line.unfoldable) {
                            this.state.expandedLines.add(line.id);
                        }
                    });
                }
            } else {
                this.state.error = result.error || "Failed to load profit and loss data";
            }
        } catch (error) {
            this.state.error = "Network error: " + error.message;
            console.error("Failed to load profit and loss:", error);
        } finally {
            this.state.loading = false;
        }
    }
    
    toggleLine(lineId) {
        if (this.state.expandedLines.has(lineId)) {
            this.state.expandedLines.delete(lineId);
            this.state.expandedLines = new Set(this.state.expandedLines);
        } else {
            this.state.expandedLines.add(lineId);
            this.state.expandedLines = new Set(this.state.expandedLines);
            
            // Load detailed accounts if needed
            const line = this.findLine(lineId);
            if (line && !line.children_loaded) {
                this.loadLineDetails(lineId);
            }
        }
    }
    
    async loadLineDetails(lineId) {
        try {
            const result = await this.rpc("/account/profit_loss/expand_line", {
                line_id: lineId,
                date_from: this.state.date_from,
                date_to: this.state.date_to,
                journals: this.state.allJournals ? null : this.state.filters.journals,
                company_id: this.user.context.company_id || false,
            });
            
            if (result.success) {
                const line = this.findLine(lineId);
                if (line) {
                    line.children = result.sub_lines;
                    line.children_loaded = true;
                    this.state.data = { ...this.state.data };
                }
            }
        } catch (error) {
            console.error("Failed to load line details:", error);
        }
    }
    
    findLine(lineId, lines = null) {
        lines = lines || this.state.data?.lines || [];
        
        for (const line of lines) {
            if (line.id === lineId) {
                return line;
            }
            if (line.children) {
                const found = this.findLine(lineId, line.children);
                if (found) return found;
            }
        }
        return null;
    }
    
    isExpanded(lineId) {
        return this.state.expandedLines.has(lineId);
    }
    
    formatCurrency(value) {
        if (!value && value !== 0) return "";
        
        const formatter = new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        
        return formatter.format(Math.abs(value));
    }
    
    getLineClass(line) {
        const classes = [`level-${line.level}`, 'profit-loss-line'];
        
        if (line.is_total) {
            classes.push('total-line');
        }
        if (line.level === 0) {
            classes.push('main-section');
        }
        if (line.unfoldable) {
            classes.push('unfoldable');
        }
        
        return classes.join(' ');
    }
    
    async onDateChange(field, event) {
        const value = event.target.value;
        this.state.filters[field] = value;
        this.state[field] = value;
        await this.loadProfitLossData();
    }
    
    async onDateRangeClick() {
        // Open date range picker dialog
        this.notification.add("Date range selection dialog coming soon", {
            type: 'info',
            title: 'Date Range'
        });
    }
    
    // Journal Filter Methods
    async onJournalChange(journalIds) {
        this.state.filters.journals = journalIds;
        this.state.allJournals = journalIds.length === 0;
        this.state.selectedJournalsCount = journalIds.length;
        await this.loadProfitLossData();
    }
    
    async toggleAllJournals() {
        this.state.allJournals = !this.state.allJournals;
        if (this.state.allJournals) {
            this.state.filters.journals = [];
            this.state.selectedJournalsCount = 0;
        } else {
            this.state.filters.journals = this.state.journals.map(j => j.id);
            this.state.selectedJournalsCount = this.state.journals.length;
        }
        await this.loadProfitLossData();
    }
    
    async onJournalToggle(journalId, event) {
        const checked = event.target.checked;
        if (checked) {
            if (!this.state.filters.journals.includes(journalId)) {
                this.state.filters.journals.push(journalId);
            }
        } else {
            const index = this.state.filters.journals.indexOf(journalId);
            if (index > -1) {
                this.state.filters.journals.splice(index, 1);
            }
        }
        this.state.selectedJournalsCount = this.state.filters.journals.length;
        this.state.allJournals = this.state.filters.journals.length === 0;
        await this.loadProfitLossData();
    }
    
    async selectJournalsByType(journalType) {
        this.state.filters.journals = [];
        this.state.allJournals = false;
        
        const journalsOfType = this.state.journals.filter(j => j.type === journalType);
        if (journalsOfType.length > 0) {
            this.state.filters.journals = journalsOfType.map(j => j.id);
            this.state.selectedJournalsCount = journalsOfType.length;
        } else {
            this.notification.add(`No ${journalType} journals found`, {
                type: 'info',
                title: 'Journal Filter'
            });
            this.state.selectedJournalsCount = 0;
        }
        
        await this.loadProfitLossData();
    }
    
    // Comparison Methods
    async setComparisonMode(mode) {
        this.state.comparisonMode = mode;
        this.state.comparison = mode !== 'none';
        
        if (mode === 'previous') {
            // Calculate previous period
            const currentFrom = new Date(this.state.date_from);
            const currentTo = new Date(this.state.date_to);
            const periodLength = currentTo - currentFrom;
            
            this.state.comparisonDateFrom = new Date(currentFrom - periodLength).toISOString().split('T')[0];
            this.state.comparisonDateTo = new Date(currentFrom - 1).toISOString().split('T')[0];
        } else if (mode === 'year') {
            // Same period last year
            const currentFrom = new Date(this.state.date_from);
            const currentTo = new Date(this.state.date_to);
            
            currentFrom.setFullYear(currentFrom.getFullYear() - 1);
            currentTo.setFullYear(currentTo.getFullYear() - 1);
            
            this.state.comparisonDateFrom = currentFrom.toISOString().split('T')[0];
            this.state.comparisonDateTo = currentTo.toISOString().split('T')[0];
        }
        
        await this.loadProfitLossData();
    }
    
    async onComparisonDateChange(field, event) {
        this.state[field] = event.target.value;
        await this.loadProfitLossData();
    }
    
    onPeriodOrderChange(event) {
        this.state.periodOrder = event.target.value;
        this.state.data = { ...this.state.data };
    }
    
    // Analytic Methods
    async openAnalyticAccounts() {
        this.notification.add("Analytic Accounts selection coming soon", {
            type: 'info',
            title: 'Analytic Filter'
        });
    }
    
    async openAnalyticPlans() {
        this.notification.add("Analytic Plans selection coming soon", {
            type: 'info',
            title: 'Analytic Filter'
        });
    }
    
    // Partner Methods
    async openPartnerSelection() {
        this.notification.add("Partner selection coming soon", {
            type: 'info',
            title: 'Partner Filter'
        });
    }
    
    // Posted Entries Methods
    async toggleDraftEntries() {
        this.state.includeDraft = !this.state.includeDraft;
        this.state.onlyPosted = !this.state.includeDraft;
        await this.loadProfitLossData();
    }
    
    async toggleAnalyticSimulations() {
        this.state.includeSimulations = !this.state.includeSimulations;
        await this.loadProfitLossData();
    }
    
    unfoldAll() {
        if (this.state.data && this.state.data.lines) {
            const expandAllLines = (lines) => {
                lines.forEach(line => {
                    if (line.unfoldable) {
                        this.state.expandedLines.add(line.id);
                        if (line.children) {
                            expandAllLines(line.children);
                        }
                    }
                });
            };
            expandAllLines(this.state.data.lines);
            this.state.expandedLines = new Set(this.state.expandedLines);
        }
    }
    
    async toggleHideZero() {
        this.state.hideZeroBalances = !this.state.hideZeroBalances;
        await this.loadProfitLossData();
    }
    
    toggleSplitView() {
        this.state.splitHorizontally = !this.state.splitHorizontally;
        this.notification.add("Split view functionality coming soon", {
            type: 'info',
            title: 'View Options'
        });
    }
    
    // Budget Methods
    async openBudgetOptions() {
        this.notification.add("Budget options coming soon", {
            type: 'info',
            title: 'Budget'
        });
    }
    
    // Export Methods
    async exportPDF() {
        const url = `/account/profit_loss/export_pdf?date_from=${this.state.date_from}&date_to=${this.state.date_to}`;
        window.open(url, '_blank');
    }
    
    async exportExcel() {
        const url = `/account/profit_loss/export_excel?date_from=${this.state.date_from}&date_to=${this.state.date_to}`;
        window.open(url, '_blank');
    }
    
    setupDatePicker() {
        // Setup date picker if needed
    }
    
    getVisibleLines(lines = null, parentExpanded = true) {
        lines = lines || this.state.data?.lines || [];
        const visibleLines = [];
        
        for (const line of lines) {
            if (parentExpanded) {
                // Apply hide zero balances filter
                if (this.state.hideZeroBalances && line.balance === 0 && !line.is_total) {
                    continue;
                }
                
                visibleLines.push(line);
                
                if (line.children && this.isExpanded(line.id)) {
                    const childLines = this.getVisibleLines(line.children, true);
                    visibleLines.push(...childLines);
                }
            }
        }
        
        return visibleLines;
    }
}

// Register the component as a client action
registry.category("actions").add("account_profit_loss_report", ProfitLossReport);