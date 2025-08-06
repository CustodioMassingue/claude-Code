/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useState, onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';

/**
 * Mozambique Accounting Dashboard Component
 * Displays key financial metrics and quick actions
 */
export class MozAccountingDashboard extends Component {
    static template = 'mozambique_accounting.Dashboard';
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');
        this.notification = useService('notification');
        
        this.state = useState({
            metrics: {
                totalRevenue: 0,
                totalExpenses: 0,
                profitMargin: 0,
                pendingInvoices: 0,
                overdueInvoices: 0,
                bankBalance: 0,
                vatToPay: 0,
                irpcToPay: 0,
            },
            loading: true,
            period: 'month', // month, quarter, year
            currency: 'MZN',
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    /**
     * Load dashboard metrics from server
     */
    async loadDashboardData() {
        try {
            const data = await this.orm.call(
                'moz.account',
                'get_dashboard_data',
                [this.state.period]
            );
            
            this.state.metrics = data;
            this.state.loading = false;
        } catch (error) {
            this.notification.add('Error loading dashboard data', {
                type: 'danger',
            });
            this.state.loading = false;
        }
    }

    /**
     * Format currency values
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('pt-MZ', {
            style: 'currency',
            currency: this.state.currency,
            minimumFractionDigits: 2,
        }).format(value);
    }

    /**
     * Calculate percentage change
     */
    calculateChange(current, previous) {
        if (previous === 0) return 0;
        return ((current - previous) / previous * 100).toFixed(1);
    }

    /**
     * Handle period change
     */
    async onPeriodChange(period) {
        this.state.period = period;
        this.state.loading = true;
        await this.loadDashboardData();
    }

    /**
     * Quick action handlers
     */
    async createInvoice() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'moz.invoice',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    async viewBankReconciliation() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'moz.bank.reconciliation',
            view_mode: 'list,form',
            target: 'current',
        });
    }

    async generateSaftReport() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'moz.saft.export.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    async viewTaxReport() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'moz.tax.report',
            view_mode: 'pivot,graph,list',
            target: 'current',
        });
    }
}

// Register the dashboard widget
registry.category('actions').add(
    'mozambique_accounting_dashboard',
    MozAccountingDashboard
);