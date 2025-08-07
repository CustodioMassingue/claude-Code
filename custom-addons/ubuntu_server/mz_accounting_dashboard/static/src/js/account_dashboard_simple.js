/** @odoo-module */

import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";

/**
 * Simple Account Dashboard Kanban Controller for Odoo 18
 * Minimal implementation without complex services
 */
export class AccountDashboardKanbanController extends KanbanController {
    // Simple controller that inherits all functionality from KanbanController
    // No custom services needed for basic functionality
}

/**
 * MZ Account Dashboard Kanban View
 * Basic view for the accounting dashboard
 */
export const MZAccountDashboardKanbanView = {
    ...kanbanView,
    Controller: AccountDashboardKanbanController,
};

// Register the view with a unique name
registry.category("views").add("mz_account_dashboard_kanban_simple", MZAccountDashboardKanbanView);