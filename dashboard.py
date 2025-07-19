#!/usr/bin/env python3
"""
Dashboard for GPU Thermal Reporting System
Provides interactive visualizations for GPU thermal data
"""

import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import requests
import json

def create_dashboard():
    """Create and configure the Dash dashboard"""
    
    # Initialize Dash app
    app = dash.Dash(__name__, 
                    external_stylesheets=[
                        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
                    ])
    
    # Dashboard layout
    app.layout = html.Div([
        # Header
        html.Div([
            html.H1([
                html.I(className="fas fa-thermometer-half", style={'marginRight': '10px'}),
                "GPU Thermal Monitoring Dashboard"
            ], style={'color': '#2c3e50', 'marginBottom': '20px'}),
            
            html.Div([
                html.Span("Real-time GPU thermal monitoring and analysis", 
                         style={'color': '#7f8c8d', 'fontSize': '16px'})
            ])
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1'}),
        
        # Filters
        html.Div([
            html.Div([
                html.Label("Date Range:", style={'fontWeight': 'bold'}),
                dcc.DatePickerRange(
                    id='date-range',
                    start_date=(datetime.now() - timedelta(days=30)).date(),
                    end_date=datetime.now().date(),
                    display_format='YYYY-MM-DD'
                )
            ], style={'margin': '10px'}),
            
            html.Div([
                html.Label("GPU ID:", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='gpu-dropdown',
                    placeholder="Select GPU...",
                    multi=True
                )
            ], style={'margin': '10px'}),
            
            html.Div([
                html.Label("Issue Type:", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='issue-type-dropdown',
                    options=[
                        {'label': 'All Issues', 'value': 'all'},
                        {'label': 'Throttled', 'value': 'throttled'},
                        {'label': 'Failed', 'value': 'failed'}
                    ],
                    value='all'
                )
            ], style={'margin': '10px'}),
            
            html.Div([
                html.Label("Node:", style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='node-dropdown',
                    placeholder="Select Node...",
                    multi=True
                )
            ], style={'margin': '10px'}),
            
            html.Div([
                html.Button("Refresh Data", id='refresh-btn', n_clicks=0,
                           style={'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 'padding': '10px 20px'})
            ], style={'margin': '10px'})
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center', 'padding': '20px', 'backgroundColor': '#f8f9fa'}),
        
        # Summary Cards
        html.Div([
            html.Div([
                html.Div(id='total-events-card', className='summary-card'),
                html.Div(id='throttled-events-card', className='summary-card'),
                html.Div(id='failed-events-card', className='summary-card'),
                html.Div(id='avg-temp-card', className='summary-card')
            ], style={'display': 'flex', 'justifyContent': 'space-around', 'flexWrap': 'wrap', 'margin': '20px 0'})
        ]),
        
        # Charts
        html.Div([
            # Time Series Chart
            html.Div([
                html.H3("GPU Thermal Events Over Time", style={'textAlign': 'center'}),
                dcc.Graph(id='time-series-chart')
            ], style={'width': '100%', 'margin': '20px 0'}),
            
            # Temperature Distribution
            html.Div([
                html.Div([
                    html.H3("Temperature Distribution", style={'textAlign': 'center'}),
                    dcc.Graph(id='temp-distribution-chart')
                ], style={'width': '50%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Events by GPU", style={'textAlign': 'center'}),
                    dcc.Graph(id='gpu-events-chart')
                ], style={'width': '50%', 'display': 'inline-block'})
            ]),
            
            # Node Analysis
            html.Div([
                html.H3("Events by Node", style={'textAlign': 'center'}),
                dcc.Graph(id='node-events-chart')
            ], style={'width': '100%', 'margin': '20px 0'}),
            
            # Data Table
            html.Div([
                html.H3("Recent Events", style={'textAlign': 'center'}),
                html.Div(id='events-table')
            ], style={'width': '100%', 'margin': '20px 0'})
        ]),
        
        # Hidden div for storing data
        html.Div(id='data-store', style={'display': 'none'})
    ])
    
    # Callbacks
    @app.callback(
        [Output('gpu-dropdown', 'options'),
         Output('node-dropdown', 'options')],
        [Input('refresh-btn', 'n_clicks')]
    )
    def update_dropdowns(n_clicks):
        """Update GPU and Node dropdowns"""
        try:
            # Get GPU list
            gpu_response = requests.get('http://localhost:5000/api/gpus')
            if gpu_response.status_code == 200:
                gpus = gpu_response.json()
                gpu_options = [{'label': gpu['gpu_id'], 'value': gpu['gpu_id']} for gpu in gpus]
            else:
                gpu_options = []
            
            # Get unique nodes from GPU data
            node_response = requests.get('http://localhost:5000/api/data')
            if node_response.status_code == 200:
                data = node_response.json()
                nodes = list(set([event['node'] for event in data if event.get('node')]))
                node_options = [{'label': node, 'value': node} for node in nodes]
            else:
                node_options = []
            
            return gpu_options, node_options
        except:
            return [], []
    
    @app.callback(
        [Output('total-events-card', 'children'),
         Output('throttled-events-card', 'children'),
         Output('failed-events-card', 'children'),
         Output('avg-temp-card', 'children')],
        [Input('date-range', 'start_date'),
         Input('date-range', 'end_date'),
         Input('refresh-btn', 'n_clicks')]
    )
    def update_summary_cards(start_date, end_date, n_clicks):
        """Update summary cards"""
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get('http://localhost:5000/api/stats', params=params)
            if response.status_code == 200:
                stats = response.json()
                
                total_events = stats.get('total_events', 0)
                events_by_type = stats.get('events_by_type', {})
                temp_stats = stats.get('temperature_stats', {})
                
                return [
                    html.Div([
                        html.H4(f"{total_events:,}", style={'color': '#2c3e50', 'margin': '0'}),
                        html.P("Total Events", style={'color': '#7f8c8d', 'margin': '5px 0'})
                    ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                    
                    html.Div([
                        html.H4(f"{events_by_type.get('throttled', 0):,}", style={'color': '#e74c3c', 'margin': '0'}),
                        html.P("Throttled", style={'color': '#7f8c8d', 'margin': '5px 0'})
                    ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                    
                    html.Div([
                        html.H4(f"{events_by_type.get('failed', 0):,}", style={'color': '#c0392b', 'margin': '0'}),
                        html.P("Failed", style={'color': '#7f8c8d', 'margin': '5px 0'})
                    ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                    
                    html.Div([
                        html.H4(f"{temp_stats.get('average', 0):.1f}°C", style={'color': '#27ae60', 'margin': '0'}),
                        html.P("Avg Temperature", style={'color': '#7f8c8d', 'margin': '5px 0'})
                    ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                ]
            else:
                return [html.P("Error loading data")] * 4
        except:
            return [html.P("Error loading data")] * 4
    
    @app.callback(
        Output('time-series-chart', 'figure'),
        [Input('date-range', 'start_date'),
         Input('date-range', 'end_date'),
         Input('gpu-dropdown', 'value'),
         Input('issue-type-dropdown', 'value'),
         Input('node-dropdown', 'value'),
         Input('refresh-btn', 'n_clicks')]
    )
    def update_time_series_chart(start_date, end_date, gpu_ids, issue_type, nodes, n_clicks):
        """Update time series chart"""
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if gpu_ids:
                params['gpu_id'] = ','.join(gpu_ids) if isinstance(gpu_ids, list) else gpu_ids
            if issue_type and issue_type != 'all':
                params['issue_type'] = issue_type
            if nodes:
                params['node'] = ','.join(nodes) if isinstance(nodes, list) else nodes
            
            response = requests.get('http://localhost:5000/api/data', params=params)
            if response.status_code == 200:
                data = response.json()
                
                if not data:
                    return go.Figure().add_annotation(
                        text="No data available for selected filters",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Group by date and issue type
                df_grouped = df.groupby([df['timestamp'].dt.date, 'issue_type']).size().reset_index(name='count')
                df_grouped['timestamp'] = pd.to_datetime(df_grouped['timestamp'])
                
                fig = px.line(df_grouped, x='timestamp', y='count', color='issue_type',
                             title='GPU Thermal Events Over Time',
                             labels={'count': 'Number of Events', 'timestamp': 'Date'})
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Number of Events",
                    hovermode='x unified',
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                return fig
            else:
                return go.Figure().add_annotation(
                    text="Error loading data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        except:
            return go.Figure().add_annotation(
                text="Error loading data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @app.callback(
        Output('temp-distribution-chart', 'figure'),
        [Input('date-range', 'start_date'),
         Input('date-range', 'end_date'),
         Input('refresh-btn', 'n_clicks')]
    )
    def update_temp_distribution_chart(start_date, end_date, n_clicks):
        """Update temperature distribution chart"""
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get('http://localhost:5000/api/data', params=params)
            if response.status_code == 200:
                data = response.json()
                
                if not data:
                    return go.Figure().add_annotation(
                        text="No data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                df = pd.DataFrame(data)
                df = df.dropna(subset=['temperature'])
                
                fig = px.histogram(df, x='temperature', color='issue_type',
                                  title='Temperature Distribution by Issue Type',
                                  labels={'temperature': 'Temperature (°C)', 'count': 'Frequency'})
                
                fig.update_layout(
                    xaxis_title="Temperature (°C)",
                    yaxis_title="Frequency",
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                return fig
            else:
                return go.Figure().add_annotation(
                    text="Error loading data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        except:
            return go.Figure().add_annotation(
                text="Error loading data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @app.callback(
        Output('gpu-events-chart', 'figure'),
        [Input('date-range', 'start_date'),
         Input('date-range', 'end_date'),
         Input('refresh-btn', 'n_clicks')]
    )
    def update_gpu_events_chart(start_date, end_date, n_clicks):
        """Update GPU events chart"""
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get('http://localhost:5000/api/stats', params=params)
            if response.status_code == 200:
                stats = response.json()
                top_gpus = stats.get('top_gpus', [])
                
                if not top_gpus:
                    return go.Figure().add_annotation(
                        text="No data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                df = pd.DataFrame(top_gpus)
                
                fig = px.bar(df, x='gpu_id', y='count',
                            title='Events by GPU',
                            labels={'gpu_id': 'GPU ID', 'count': 'Number of Events'})
                
                fig.update_layout(
                    xaxis_title="GPU ID",
                    yaxis_title="Number of Events",
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                return fig
            else:
                return go.Figure().add_annotation(
                    text="Error loading data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        except:
            return go.Figure().add_annotation(
                text="Error loading data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @app.callback(
        Output('node-events-chart', 'figure'),
        [Input('date-range', 'start_date'),
         Input('date-range', 'end_date'),
         Input('refresh-btn', 'n_clicks')]
    )
    def update_node_events_chart(start_date, end_date, n_clicks):
        """Update node events chart"""
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get('http://localhost:5000/api/stats', params=params)
            if response.status_code == 200:
                stats = response.json()
                events_by_node = stats.get('events_by_node', [])
                
                if not events_by_node:
                    return go.Figure().add_annotation(
                        text="No data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                df = pd.DataFrame(events_by_node)
                
                fig = px.pie(df, values='count', names='node',
                            title='Events by Node')
                
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                return fig
            else:
                return go.Figure().add_annotation(
                    text="Error loading data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        except:
            return go.Figure().add_annotation(
                text="Error loading data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    
    @app.callback(
        Output('events-table', 'children'),
        [Input('date-range', 'start_date'),
         Input('date-range', 'end_date'),
         Input('refresh-btn', 'n_clicks')]
    )
    def update_events_table(start_date, end_date, n_clicks):
        """Update events table"""
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get('http://localhost:5000/api/data', params=params)
            if response.status_code == 200:
                data = response.json()
                
                if not data:
                    return html.P("No data available for selected filters")
                
                # Create table rows
                table_rows = []
                for event in data[:50]:  # Show last 50 events
                    row = html.Tr([
                        html.Td(event.get('node', '')),
                        html.Td(event.get('gpu_id', '')),
                        html.Td(event.get('timestamp', '')[:10] if event.get('timestamp') else ''),
                        html.Td(f"{event.get('temperature', 0):.1f}°C" if event.get('temperature') else ''),
                        html.Td(event.get('issue_type', '')),
                        html.Td(event.get('reason', ''))
                    ])
                    table_rows.append(row)
                
                table = html.Table([
                    html.Thead(html.Tr([
                        html.Th("Node"),
                        html.Th("GPU ID"),
                        html.Th("Date"),
                        html.Th("Temperature"),
                        html.Th("Issue Type"),
                        html.Th("Reason")
                    ])),
                    html.Tbody(table_rows)
                ], style={'width': '100%', 'borderCollapse': 'collapse'})
                
                return table
            else:
                return html.P("Error loading data")
        except:
            return html.P("Error loading data")
    
    return app 