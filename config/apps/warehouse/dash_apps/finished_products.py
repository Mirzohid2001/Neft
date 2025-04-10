import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from django_plotly_dash import DjangoDash
import plotly.express as px
from warehouse.models import Product

app = DjangoDash('ProductTrend')

def get_product_data():
    qs = Product.objects.all()
    data = {
        'Product': [p.name for p in qs],
        'Net Quantity': [p.in_qty - p.out_qty for p in qs]
    }
    return data

app.layout = html.Div([
    dcc.Graph(id='product-trend-chart'),
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0)
])

@app.callback(
    Output('product-trend-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_chart(n):
    data = get_product_data()
    fig = px.bar(data, x='Product', y='Net Quantity', title="Mahsulotlarga qarab Net miqdor")
    return fig
