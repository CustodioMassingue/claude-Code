# -*- coding: utf-8 -*-

from . import models
from . import wizards
from . import controllers
from . import reports

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Post-installation hook to initialize Enterprise features
    """
    
    try:
        # Create default dashboards if needed
        _logger.info("Initializing Account Enterprise Replica...")
        
        # Create default consolidation chart
        Chart = env['account.consolidation.chart']
        if not Chart.search([]):
            Chart.create_default_chart()
        
        # Initialize cache
        Cache = env['account.enterprise.cache']
        Cache.init_cache()
        
        _logger.info("Account Enterprise Replica initialized successfully!")
        
    except Exception as e:
        _logger.error(f"Error during post-init hook: {str(e)}")


def uninstall_hook(cr, registry):
    """
    Uninstall hook to cleanup Enterprise features
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Cleanup cache
        Cache = env['account.enterprise.cache']
        Cache.cleanup_cache()
        
        # Archive consolidation data
        Chart = env['account.consolidation.chart']
        for chart in Chart.search([]):
            chart.archive_all_data()
            
        _logger.info("Account Enterprise Replica uninstalled successfully!")
        
    except Exception as e:
        _logger.error(f"Error during uninstall hook: {str(e)}")