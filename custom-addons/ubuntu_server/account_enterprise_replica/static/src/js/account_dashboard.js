/** @odoo-module **/

import { Component, useState, onWillStart, useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AccountEnterpriseDashboard extends Component {
    static template = "account_enterprise_replica.Dashboard";
    static props = {
        action: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            dashboardData: {},
            kpis: {},
            charts: {},
            period: 'month',
            isLoading: true,
        });
        
        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call(
                'account.enterprise.dashboard',
                'get_dashboard_data',
                [],
                { period: this.state.period }
            );
            
            this.state.dashboardData = data;
            this.state.kpis = data.kpis || {};
            this.state.charts = data.charts || {};
        } catch (error) {
            this.notification.add(_t("Failed to load dashboard data"), {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    async onPeriodChange(ev) {
        this.state.period = ev.target.value;
        await this.loadDashboardData();
    }

    async refreshDashboard() {
        await this.loadDashboardData();
        this.notification.add(_t("Dashboard refreshed"), {
            type: "success",
        });
    }

    async exportToExcel() {
        const action = await this.orm.call(
            'account.enterprise.dashboard',
            'export_to_excel',
            [this.props.action.context.active_id]
        );
        this.action.doAction(action);
    }

    async exportToPDF() {
        const action = await this.orm.call(
            'account.enterprise.dashboard',
            'export_to_pdf',
            [this.props.action.context.active_id]
        );
        this.action.doAction(action);
    }

    formatCurrency(value) {
        if (!value) return "0.00";
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    formatPercentage(value) {
        if (!value) return "0%";
        return `${(value * 100).toFixed(2)}%`;
    }

    getKPIClass(kpi) {
        if (!kpi || !kpi.trend) return "";
        return kpi.trend > 0 ? "text-success" : "text-danger";
    }

    getKPIIcon(kpi) {
        if (!kpi || !kpi.trend) return "";
        return kpi.trend > 0 ? "fa-arrow-up" : "fa-arrow-down";
    }
}

registry.category("actions").add("account_enterprise_dashboard", AccountEnterpriseDashboard);