/** @odoo-module **/

import { Component, useState, onWillStart } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { standardFieldProps } from '@web/views/fields/standard_field_props';

/**
 * Bank Reconciliation Widget for Mozambique Accounting
 * Provides intelligent matching and reconciliation features
 */
export class BankReconciliationWidget extends Component {
    static template = 'mozambique_accounting.BankReconciliation';
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService('orm');
        this.notification = useService('notification');
        
        this.state = useState({
            bankLines: [],
            suggestions: [],
            selectedLines: new Set(),
            filters: {
                dateFrom: null,
                dateTo: null,
                amountMin: null,
                amountMax: null,
                partner: null,
                showReconciled: false,
            },
            loading: false,
            currentPage: 1,
            totalPages: 1,
        });

        onWillStart(async () => {
            await this.loadBankLines();
        });
    }

    /**
     * Load unreconciled bank statement lines
     */
    async loadBankLines() {
        this.state.loading = true;
        try {
            const domain = this._buildDomain();
            const lines = await this.orm.searchRead(
                'moz.bank.statement.line',
                domain,
                ['date', 'name', 'amount', 'partner_id', 'reconciled'],
                { limit: 50, offset: (this.state.currentPage - 1) * 50 }
            );
            
            this.state.bankLines = lines;
            await this.loadSuggestions();
        } catch (error) {
            this.notification.add('Error loading bank lines', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Build domain based on filters
     */
    _buildDomain() {
        const domain = [];
        
        if (!this.state.filters.showReconciled) {
            domain.push(['reconciled', '=', false]);
        }
        
        if (this.state.filters.dateFrom) {
            domain.push(['date', '>=', this.state.filters.dateFrom]);
        }
        
        if (this.state.filters.dateTo) {
            domain.push(['date', '<=', this.state.filters.dateTo]);
        }
        
        if (this.state.filters.partner) {
            domain.push(['partner_id', '=', this.state.filters.partner]);
        }
        
        return domain;
    }

    /**
     * Load reconciliation suggestions using AI matching
     */
    async loadSuggestions() {
        for (const line of this.state.bankLines) {
            if (line.reconciled) continue;
            
            const suggestions = await this.orm.call(
                'moz.bank.reconciliation',
                'get_reconciliation_suggestions',
                [line.id]
            );
            
            line.suggestions = suggestions;
        }
    }

    /**
     * Apply automatic reconciliation
     */
    async autoReconcile() {
        const selectedIds = Array.from(this.state.selectedLines);
        
        if (selectedIds.length === 0) {
            this.notification.add('Please select lines to reconcile', { 
                type: 'warning' 
            });
            return;
        }
        
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                'moz.bank.reconciliation',
                'auto_reconcile',
                [selectedIds]
            );
            
            this.notification.add(
                `Successfully reconciled ${result.count} lines`,
                { type: 'success' }
            );
            
            await this.loadBankLines();
            this.state.selectedLines.clear();
        } catch (error) {
            this.notification.add('Reconciliation failed', { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Manual reconciliation with selected invoice
     */
    async reconcileWithInvoice(lineId, invoiceId) {
        try {
            await this.orm.call(
                'moz.bank.reconciliation',
                'reconcile_with_invoice',
                [lineId, invoiceId]
            );
            
            this.notification.add('Line reconciled successfully', { 
                type: 'success' 
            });
            
            await this.loadBankLines();
        } catch (error) {
            this.notification.add('Reconciliation failed', { type: 'danger' });
        }
    }

    /**
     * Create new payment from bank line
     */
    async createPayment(lineId) {
        const line = this.state.bankLines.find(l => l.id === lineId);
        
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'moz.payment',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_amount: line.amount,
                default_payment_date: line.date,
                default_bank_line_id: line.id,
                default_name: line.name,
            },
        });
    }

    /**
     * Toggle line selection
     */
    toggleSelection(lineId) {
        if (this.state.selectedLines.has(lineId)) {
            this.state.selectedLines.delete(lineId);
        } else {
            this.state.selectedLines.add(lineId);
        }
    }

    /**
     * Apply filters
     */
    async applyFilters() {
        this.state.currentPage = 1;
        await this.loadBankLines();
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.state.filters = {
            dateFrom: null,
            dateTo: null,
            amountMin: null,
            amountMax: null,
            partner: null,
            showReconciled: false,
        };
        this.applyFilters();
    }
}

// Register the widget
registry.category('fields').add(
    'bank_reconciliation_widget',
    BankReconciliationWidget
);