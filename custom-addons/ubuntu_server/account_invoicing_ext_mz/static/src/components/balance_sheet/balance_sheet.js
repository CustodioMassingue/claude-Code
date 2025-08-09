/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BalanceSheetReport extends Component {
    static template = "account_invoicing_ext_mz.BalanceSheetReport";
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
            date_to: this.getDefaultDate(),
            date_from: null,
            comparison: false,
            journals: [],
            allJournals: true,
            selectedJournalsCount: 0,
            showAnalytic: false,
            onlyPosted: true,
            hasUnposted: false,
            hideZeroBalances: false,
            filters: {
                date_to: this.getDefaultDate(),
                date_from: null,
                journals: [],
                comparison: false,
            }
        });
        
        onWillStart(async () => {
            await this.loadJournals();
            await this.loadBalanceSheetData();
        });
        
        onMounted(() => {
            this.setupDatePicker();
        });
    }
    
    getDefaultDate() {
        const today = new Date();
        return today.toISOString().split('T')[0];
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
    
    async loadBalanceSheetData() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const result = await this.rpc("/account/balance_sheet/data", {
                date_to: this.state.date_to,
                date_from: this.state.date_from,
                journals: this.state.allJournals ? null : this.state.filters.journals,
                company_id: this.user.context.company_id || false,
                comparison: this.state.comparison,
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
                this.state.error = result.error || "Failed to load balance sheet data";
            }
        } catch (error) {
            this.state.error = "Network error: " + error.message;
            console.error("Failed to load balance sheet:", error);
        } finally {
            this.state.loading = false;
        }
    }
    
    toggleLine(lineId) {
        if (this.state.expandedLines.has(lineId)) {
            this.state.expandedLines.delete(lineId);
            // Force re-render by creating new Set
            this.state.expandedLines = new Set(this.state.expandedLines);
        } else {
            this.state.expandedLines.add(lineId);
            // Force re-render by creating new Set
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
            const result = await this.rpc("/account/balance_sheet/expand_line", {
                line_id: lineId,
                date_to: this.state.date_to,
                journals: this.state.allJournals ? null : this.state.filters.journals,
                company_id: this.user.context.company_id || false,
            });
            
            if (result.success) {
                const line = this.findLine(lineId);
                if (line) {
                    line.children = result.sub_lines;
                    line.children_loaded = true;
                    // Force re-render
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
        const classes = [`level-${line.level}`, 'balance-sheet-line'];
        
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
        await this.loadBalanceSheetData();
    }
    
    async onJournalChange(journalIds) {
        this.state.filters.journals = journalIds;
        this.state.allJournals = journalIds.length === 0;
        this.state.selectedJournalsCount = journalIds.length;
        await this.loadBalanceSheetData();
    }
    
    async toggleAllJournals() {
        this.state.allJournals = !this.state.allJournals;
        if (this.state.allJournals) {
            this.state.filters.journals = [];
            this.state.selectedJournalsCount = 0;
        } else {
            // Select all journals
            this.state.filters.journals = this.state.journals.map(j => j.id);
            this.state.selectedJournalsCount = this.state.journals.length;
        }
        await this.loadBalanceSheetData();
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
        await this.loadBalanceSheetData();
    }
    
    async onComparisonToggle() {
        this.state.comparison = !this.state.comparison;
        await this.loadBalanceSheetData();
    }
    
    async onAnalyticToggle() {
        this.state.showAnalytic = !this.state.showAnalytic;
        // Implement analytic filtering
    }
    
    async onPostedEntriesToggle() {
        this.state.onlyPosted = !this.state.onlyPosted;
        await this.loadBalanceSheetData();
    }
    
    async exportPDF() {
        const url = `/account/balance_sheet/export_pdf?date_to=${this.state.date_to}`;
        window.open(url, '_blank');
    }
    
    async exportExcel() {
        const url = `/account/balance_sheet/export_excel?date_to=${this.state.date_to}`;
        window.open(url, '_blank');
    }
    
    setupDatePicker() {
        // Setup date picker if needed
        const dateInput = document.querySelector('.date-filter input');
        if (dateInput) {
            dateInput.addEventListener('change', (e) => {
                this.onDateChange('date_to', e);
            });
        }
    }
    
    getVisibleLines(lines = null, parentExpanded = true) {
        lines = lines || this.state.data?.lines || [];
        const visibleLines = [];
        
        for (const line of lines) {
            if (parentExpanded) {
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
registry.category("actions").add("account_balance_sheet_report", BalanceSheetReport);