/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useRef, onMounted } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MzDashboardGraphField extends Component {
    static template = "mz_accounting_dashboard.MzDashboardGraphField";
    static props = {
        ...standardFieldProps,
    };
    
    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        
        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js");
        });
        
        onMounted(() => {
            this.renderChart();
        });
    }
    
    renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas || !window.Chart) return;
        
        const ctx = canvas.getContext('2d');
        const journalType = this.props.record.data.type || 'general';
        
        // Generate sample data
        const data = this.generateSampleData(journalType);
        
        // Create gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
        if (journalType === 'sale') {
            gradient.addColorStop(0, 'rgba(124, 77, 255, 0.8)');
            gradient.addColorStop(1, 'rgba(124, 77, 255, 0.1)');
        } else if (journalType === 'purchase') {
            gradient.addColorStop(0, 'rgba(255, 99, 132, 0.8)');
            gradient.addColorStop(1, 'rgba(255, 99, 132, 0.1)');
        } else if (journalType === 'bank') {
            gradient.addColorStop(0, 'rgba(54, 162, 235, 0.8)');
            gradient.addColorStop(1, 'rgba(54, 162, 235, 0.1)');
        } else {
            gradient.addColorStop(0, 'rgba(75, 192, 192, 0.8)');
            gradient.addColorStop(1, 'rgba(75, 192, 192, 0.1)');
        }
        
        const chartType = (journalType === 'bank' || journalType === 'cash') ? 'line' : 'bar';
        
        this.chart = new window.Chart(ctx, {
            type: chartType,
            data: {
                labels: data.labels,
                datasets: [{
                    label: data.label,
                    data: data.values,
                    backgroundColor: gradient,
                    borderColor: journalType === 'sale' ? 'rgb(124, 77, 255)' :
                                journalType === 'purchase' ? 'rgb(255, 99, 132)' :
                                journalType === 'bank' ? 'rgb(54, 162, 235)' :
                                'rgb(75, 192, 192)',
                    borderWidth: 2,
                    fill: true,
                    tension: chartType === 'line' ? 0.4 : 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 10,
                        cornerRadius: 4,
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: '#666',
                            font: {
                                size: 10,
                            },
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: journalType !== 'bank',
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                        },
                        ticks: {
                            color: '#666',
                            font: {
                                size: 10,
                            },
                        }
                    }
                }
            }
        });
    }
    
    generateSampleData(journalType) {
        const days = 7;
        const labels = [];
        const values = [];
        const today = new Date();
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
            
            if (journalType === 'sale') {
                values.push(Math.floor(Math.random() * 5) + 2);
            } else if (journalType === 'purchase') {
                values.push(Math.floor(Math.random() * 3) + 1);
            } else if (journalType === 'bank') {
                const base = 50000;
                values.push(base + (Math.random() - 0.5) * 10000);
            } else {
                values.push(Math.floor(Math.random() * 10));
            }
        }
        
        return {
            labels: labels,
            values: values,
            label: journalType === 'sale' ? 'Invoices' :
                   journalType === 'purchase' ? 'Bills' :
                   journalType === 'bank' ? 'Balance' : 'Count'
        };
    }
}

registry.category("fields").add("mz_dashboard_graph", {
    component: MzDashboardGraphField,
});