# -*- coding: utf-8 -*-
from . import models

def post_init_hook(env):
    """
    Post-installation hook
    Set all existing journals to show on dashboard by default
    """
    journals = env['account.journal'].search([])
    journals.write({'show_on_dashboard': True})
    
    # Set default colors for journals based on type
    for journal in journals:
        if journal.type == 'sale':
            journal.color = 0  # Purple gradient
        elif journal.type == 'purchase':
            journal.color = 1  # Pink gradient
        elif journal.type == 'bank':
            journal.color = 2  # Blue gradient
        elif journal.type == 'cash':
            journal.color = 3  # Green gradient
        else:
            journal.color = 4  # Orange gradient

def uninstall_hook(env):
    """
    Uninstall hook
    Clean up any dashboard-specific data
    """
    # Reset show_on_dashboard field to False
    journals = env['account.journal'].search([])
    journals.write({'show_on_dashboard': False})