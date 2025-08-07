/** @odoo-module */

import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

/**
 * Account Dashboard Kanban Controller
 * Enhanced controller for the accounting dashboard with real-time updates
 * Compatible with Odoo 18
 */
export class AccountDashboardKanbanController extends KanbanController {
    setup() {
        super.setup();
        // Use only available services in Odoo 18
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        // Note: user service might not be available in all contexts
        
        this.state = useState({
            dashboardData: {},
            isLoading: false,
            companyId: 1, // Default company ID
        });
        
        // Load dashboard data on component start
        onWillStart(async () => {
            await this.loadDashboardData();
        });
        
        // Set up auto-refresh every 60 seconds
        onMounted(() => {
            this.startAutoRefresh();
        });
    }
    
    /**
     * Load dashboard data from the server
     * Using ORM service for Odoo 18 compatibility
     */
    async loadDashboardData() {
        try {
            this.state.isLoading = true;
            // Using ORM service call method for Odoo 18
            const data = await this.orm.call(
                "account.journal",
                "get_journal_dashboard_datas",
                []
            );
            this.state.dashboardData = data;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("Error loading dashboard data", {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Start auto-refresh timer
     */
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 60000); // Refresh every 60 seconds
    }
    
    /**
     * Clean up when component is destroyed
     */
    willUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
    
    /**
     * Handle click on journal card
     */
    async onJournalCardClick(journalId, journalType) {
        // Open appropriate view based on journal type
        let action = {};
        
        switch (journalType) {
            case 'sale':
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Customer Invoices',
                    res_model: 'account.move',
                    view_mode: 'list,form',
                    views: [[false, 'list'], [false, 'form']],
                    domain: [
                        ['journal_id', '=', journalId],
                        ['move_type', 'in', ['out_invoice', 'out_refund']]
                    ],
                    context: {
                        default_journal_id: journalId,
                        default_move_type: 'out_invoice',
                    },
                };
                break;
            case 'purchase':
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Vendor Bills',
                    res_model: 'account.move',
                    view_mode: 'list,form',
                    views: [[false, 'list'], [false, 'form']],
                    domain: [
                        ['journal_id', '=', journalId],
                        ['move_type', 'in', ['in_invoice', 'in_refund']]
                    ],
                    context: {
                        default_journal_id: journalId,
                        default_move_type: 'in_invoice',
                    },
                };
                break;
            case 'bank':
            case 'cash':
                action = {
                    type: 'ir.actions.act_window',
                    name: journalType === 'bank' ? 'Bank Transactions' : 'Cash Transactions',
                    res_model: 'account.move',
                    view_mode: 'list,form',
                    views: [[false, 'list'], [false, 'form']],
                    domain: [['journal_id', '=', journalId]],
                    context: {
                        default_journal_id: journalId,
                    },
                };
                break;
            default:
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Journal Entries',
                    res_model: 'account.move',
                    view_mode: 'list,form',
                    views: [[false, 'list'], [false, 'form']],
                    domain: [['journal_id', '=', journalId]],
                    context: {
                        default_journal_id: journalId,
                    },
                };
        }
        
        this.action.doAction(action);
    }
    
    /**
     * Create new invoice/bill/payment
     */
    async onCreateNew(journalId, journalType) {
        let action = {};
        
        switch (journalType) {
            case 'sale':
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Create Customer Invoice',
                    res_model: 'account.move',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    context: {
                        default_journal_id: journalId,
                        default_move_type: 'out_invoice',
                    },
                    target: 'current',
                };
                break;
            case 'purchase':
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Create Vendor Bill',
                    res_model: 'account.move',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    context: {
                        default_journal_id: journalId,
                        default_move_type: 'in_invoice',
                    },
                    target: 'current',
                };
                break;
            case 'bank':
            case 'cash':
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Register Payment',
                    res_model: 'account.payment',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    context: {
                        default_journal_id: journalId,
                        default_payment_type: 'inbound',
                    },
                    target: 'current',
                };
                break;
            default:
                action = {
                    type: 'ir.actions.act_window',
                    name: 'Create Journal Entry',
                    res_model: 'account.move',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    context: {
                        default_journal_id: journalId,
                        default_move_type: 'entry',
                    },
                    target: 'current',
                };
        }
        
        this.action.doAction(action);
    }
    
    /**
     * Open reconciliation view
     */
    async onReconcile(journalId) {
        const action = {
            type: 'ir.actions.client',
            tag: 'bank_statement_reconciliation_view',
            context: {
                statement_line_ids: [],
                company_ids: [this.state.companyId],
                journal_id: journalId,
            },
        };
        
        this.action.doAction(action);
    }
    
    /**
     * Upload document (for purchase journal)
     */
    async onUploadDocument(journalId) {
        const action = {
            type: 'ir.actions.act_window',
            name: 'Upload Vendor Bill',
            res_model: 'account.move',
            view_mode: 'form',
            views: [[false, 'form']],
            context: {
                default_journal_id: journalId,
                default_move_type: 'in_invoice',
                default_upload_mode: true,
            },
            target: 'current',
        };
        
        this.action.doAction(action);
    }
    
    /**
     * Refresh dashboard data
     */
    async onRefreshDashboard() {
        await this.loadDashboardData();
        this.notification.add("Dashboard refreshed", {
            type: "success",
        });
    }
}

/**
 * MZ Dashboard Graph Widget Component
 * Renders mini graphs in journal cards
 */
export class MZDashboardGraphWidget extends Component {
    static template = "mz_accounting_dashboard.MZDashboardGraph";
    
    setup() {
        this.canvasRef = useRef("canvas");
        
        onMounted(() => {
            this.renderGraph();
        });
    }
    
    renderGraph() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.props.value ? JSON.parse(this.props.value) : { values: [] };
        
        if (!data.values || data.values.length === 0) {
            return;
        }
        
        // Simple line graph implementation
        const width = canvas.width;
        const height = canvas.height;
        const padding = 10;
        const graphWidth = width - (padding * 2);
        const graphHeight = height - (padding * 2);
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Find max value for scaling
        const maxValue = Math.max(...data.values.map(v => v.y), 1);
        const points = data.values.length;
        
        // Draw line
        ctx.beginPath();
        ctx.strokeStyle = '#875A7B';
        ctx.lineWidth = 2;
        
        data.values.forEach((point, index) => {
            const x = padding + (index / (points - 1)) * graphWidth;
            const y = padding + graphHeight - (point.y / maxValue) * graphHeight;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw points
        data.values.forEach((point, index) => {
            const x = padding + (index / (points - 1)) * graphWidth;
            const y = padding + graphHeight - (point.y / maxValue) * graphHeight;
            
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fillStyle = '#875A7B';
            ctx.fill();
        });
    }
}

// Register the graph widget with unique name
registry.category("fields").add("mz_dashboard_graph", {
    component: MZDashboardGraphWidget,
});

/**
 * MZ Account Dashboard Kanban View
 * Custom view for the accounting dashboard
 */
export const MZAccountDashboardKanbanView = {
    ...kanbanView,
    Controller: AccountDashboardKanbanController,
    buttonTemplate: "mz_accounting_dashboard.KanbanButtons",
};

// Register the custom kanban view with unique name
registry.category("views").add("mz_account_dashboard_kanban", MZAccountDashboardKanbanView);