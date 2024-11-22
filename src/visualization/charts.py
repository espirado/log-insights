# src/visualization/charts.py
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

class ChartGenerator:
    def __init__(self, theme: str = "plotly"):
        self.theme = theme
        self.colors = {
            'Critical': '#ff0000',
            'High': '#ff9900',
            'Medium': '#ffff00',
            'Low': '#00ff00',
            'kubernetes': '#326CE5',
            'database': '#336791',
            'infrastructure': '#FF9900',
            'application': '#00ACC1'
        }

    def create_dashboard(self, analysis_results: dict, filename: str = 'log_analysis_dashboard.html'):
        """Create a comprehensive dashboard with multiple visualizations"""
        # Create figure with subplots, specifying correct types
        fig_charts = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Issues by Context',
                'Severity Distribution',
                'Timeline Analysis',
                'Issue Categories'
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "bar"}]
            ]
        )

        # Add visualizations
        self._add_context_distribution(fig_charts, analysis_results, 1, 1)
        self._add_severity_distribution(fig_charts, analysis_results, 1, 2)
        self._add_timeline(fig_charts, analysis_results, 2, 1)
        self._add_category_distribution(fig_charts, analysis_results, 2, 2)

        fig_charts.update_layout(
            height=800,
            showlegend=True,
            title={
                'text': 'Log Analysis Dashboard',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            }
        )

        # Create additional visualizations
        fig_summary = self._create_summary_table(analysis_results)
        fig_details = self._create_detailed_table(analysis_results)
        fig_analysis = self._create_root_cause_analysis(analysis_results)

        # Save to HTML
        with open(filename, 'w') as f:
            f.write("""
            <html>
                <head>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                        }
                        .container {
                            max-width: 1200px;
                            margin: 0 auto;
                            padding: 20px;
                        }
                        .chart-container {
                            background: white;
                            margin-bottom: 30px;
                            padding: 20px;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }
                        .section-title {
                            font-size: 24px;
                            color: #333;
                            margin: 20px 0;
                            padding-bottom: 10px;
                            border-bottom: 2px solid #eee;
                        }
                        .grid-container {
                            display: grid;
                            grid-gap: 20px;
                            margin-top: 20px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="chart-container">
                            <div class="section-title">Metrics Overview</div>
            """)
            f.write(fig_charts.to_html(full_html=False, include_plotlyjs=True))
            f.write('</div>')
            
            f.write('<div class="chart-container">')
            f.write('<div class="section-title">Summary Statistics</div>')
            f.write(fig_summary.to_html(full_html=False, include_plotlyjs=False))
            f.write('</div>')
            
            f.write('<div class="chart-container">')
            f.write('<div class="section-title">Root Cause Analysis</div>')
            f.write(fig_analysis.to_html(full_html=False, include_plotlyjs=False))
            f.write('</div>')
            
            f.write('<div class="chart-container">')
            f.write('<div class="section-title">Detailed Log Analysis</div>')
            f.write(fig_details.to_html(full_html=False, include_plotlyjs=False))
            f.write('</div>')
            
            f.write('</div></body></html>')

    def _add_context_distribution(self, fig, results, row, col):
        """Add context distribution pie chart"""
        issues = results['results']['issues']
        fig.add_trace(
            go.Pie(
                labels=list(issues.keys()),
                values=list(issues.values()),
                name="Contexts",
                marker=dict(colors=[self.colors.get(ctx, '#808080') for ctx in issues.keys()]),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>"
            ),
            row=row, col=col
        )

    def _add_severity_distribution(self, fig, results, row, col):
        """Add severity distribution bar chart"""
        severities = results['results']['severities']
        fig.add_trace(
            go.Bar(
                x=list(severities.keys()),
                y=list(severities.values()),
                name="Severity",
                marker_color=[self.colors.get(sev, '#808080') for sev in severities.keys()],
                hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
            ),
            row=row, col=col
        )

    def _add_timeline(self, fig, results, row, col):
        """Add timeline analysis"""
        df = pd.DataFrame(results['results']['timeline'])
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            for context in df['context'].unique():
                context_data = df[df['context'] == context]
                fig.add_trace(
                    go.Scatter(
                        x=context_data['timestamp'],
                        y=context_data['severity'],
                        name=context,
                        mode='markers+lines',
                        marker=dict(size=8, color=self.colors.get(context, '#808080')),
                        hovertemplate=(
                            "<b>%{x}</b><br>" +
                            "Severity: %{y}<br>" +
                            "Context: " + context + "<br>" +
                            "<extra></extra>"
                        )
                    ),
                    row=row, col=col
                )

    def _add_category_distribution(self, fig, results, row, col):
        """Add category distribution"""
        categories = {}
        for entry in results['results']['timeline']:
            cat = entry.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
        fig.add_trace(
            go.Bar(
                x=list(categories.keys()),
                y=list(categories.values()),
                name="Categories",
                marker_color='#2E86C1',
                hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
            ),
            row=row, col=col
        )

    def _create_summary_table(self, results):
        """Create summary table with enhanced metrics"""
        metrics = self._calculate_summary_metrics(results)
        
        return go.Figure(data=[go.Table(
            header=dict(
                values=['<b>Metric</b>', '<b>Value</b>'],
                font=dict(size=12),
                fill_color='#2E86C1',
                align='left',
                font_color='white'
            ),
            cells=dict(
                values=[list(metrics.keys()), list(metrics.values())],
                font=dict(size=11),
                fill_color=[['white', '#f9f9f9'] * len(metrics)],
                align='left'
            )
        )])

    def _create_detailed_table(self, results):
        """Create detailed analysis table"""
        df = pd.DataFrame(results['results']['timeline'])
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return go.Figure(data=[go.Table(
            header=dict(
                values=[
                    '<b>Timestamp</b>', 
                    '<b>Context</b>', 
                    '<b>Category</b>', 
                    '<b>Severity</b>',
                    '<b>Root Cause</b>',
                    '<b>Remediation</b>'
                ],
                font=dict(size=12),
                fill_color='#2E86C1',
                align='left',
                font_color='white'
            ),
            cells=dict(
                values=[
                    df['timestamp'],
                    df['context'],
                    df['category'],
                    df['severity'],
                    df['root_cause'],
                    df['remediation']
                ],
                font=dict(size=11),
                fill_color=[['white', '#f9f9f9'] * len(df)],
                align='left',
                height=30
            )
        )])

    def _create_root_cause_analysis(self, results):
        """Create root cause analysis visualization"""
        df = pd.DataFrame(results['results']['timeline'])
        if df.empty:
            return go.Figure()

        root_cause_counts = df['root_cause'].value_counts()
        
        return go.Figure(data=[go.Bar(
            x=root_cause_counts.values,
            y=root_cause_counts.index,
            orientation='h',
            marker_color='#2E86C1',
            hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>"
        )]).update_layout(
            title="Root Cause Distribution",
            xaxis_title="Count",
            yaxis_title="Root Cause",
            height=400
        )

    def _calculate_summary_metrics(self, results):
        """Calculate summary metrics"""
        timeline = results['results']['timeline']
        total_issues = len(timeline)
        
        df = pd.DataFrame(timeline)
        root_causes = df['root_cause'].value_counts().head(3).to_dict() if not df.empty else {}
        
        metrics = {
            'Total Issues Analyzed': total_issues,
            'Unique Contexts': len(results['results']['issues']),
            'Most Common Context': max(results['results']['issues'].items(), key=lambda x: x[1])[0] if results['results']['issues'] else 'N/A',
            'Most Common Severity': max(results['results']['severities'].items(), key=lambda x: x[1])[0] if results['results']['severities'] else 'N/A',
            'Critical Issues': results['results']['severities'].get('Critical', 0),
            'High Severity Issues': results['results']['severities'].get('High', 0)
        }
        
        for i, (cause, count) in enumerate(root_causes.items(), 1):
            metrics[f'Top {i} Root Cause'] = f"{cause} ({count} occurrences)"
        
        return metrics