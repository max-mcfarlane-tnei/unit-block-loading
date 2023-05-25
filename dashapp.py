import os.path
import pickle

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import exceptions
from run import run_basic_example

header_height = 8

# Create the Dash application
dashapp = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

days = 6
generators = 3
target_60 = 2
target_100 = 4
block_limit = 500
min_operating_capacity = 0.15

# if True or not os.path.exists('./subplot_fig.p'):
if not os.path.exists('./subplot_fig.p'):
    decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig = run_basic_example(
        t=48 * days, n=generators, restart_targets=((target_60, 0.6), (target_100, 1)),
        block_limit=block_limit, min_operating_capacity=min_operating_capacity
    )
    pickle.dump(subplot_fig, open('./subplot_fig.p', 'wb'))
else:
    subplot_fig = pickle.load(open('./subplot_fig.p', 'rb'))

dashapp.layout = html.Div(
    children=dbc.Row([
        html.H3("Block Loading Optimisation - Playground", style={
            "background-color": "#000936",
            "color": "white", "margin": "0px", "padding": "20px", "height": f"{header_height}vh"
        }),
        dbc.Col([

            dcc.Loading(
                id="loading",
                type="default",
                children=[
                    # Add the header with background color
                    html.Div(
                        children=[
                            dcc.Graph(
                                id="my-graph",
                                figure=subplot_fig,
                                style={"height": "100%"}
                            )
                        ],
                        style={"width": "100%", "height": f"{100 - (2 * header_height)}vh", 'overflow-y': 'hidden'},
                        # Set the div to fill the page
                    ),
                ]
            )
        ], className="m-2 col-8"),
        dbc.Col([

            dbc.Card(
                [
                    dbc.CardHeader("Options"),
                    dbc.CardBody(
                        [
                            html.Label("Days"),
                            dcc.Slider(
                                id="days-slider",
                                min=1,
                                max=10,
                                step=1,
                                value=days,
                                marks={i: str(i) for i in range(1, 11)},
                            ),
                            html.Br(),
                            html.Label("Generators"),
                            dcc.Slider(
                                id="generators-slider",
                                min=1,
                                max=10,
                                step=1,
                                value=generators,
                                marks={i: str(i) for i in range(1, 11)},
                            ),
                            html.Br(),
                            html.Label("Target 60%"),
                            dcc.Slider(
                                id="target-60-slider",
                                min=0,
                                max=10,
                                step=0.5,
                                value=target_60,
                                marks={i: str(i) for i in range(11)},
                            ),
                            html.Br(),
                            html.Label("Target 100%"),
                            dcc.Slider(
                                id="target-100-slider",
                                min=0,
                                max=10,
                                step=0.5,
                                value=target_100,
                                marks={i: str(i) for i in range(11)},
                            ),
                            html.Br(),
                            html.Label("Block Limit"),
                            dcc.Slider(
                                id="block-limit-slider",
                                min=0,
                                max=1000,
                                step=100,
                                value=block_limit,
                                marks={i: str(i) for i in range(0, 1001, 200)},
                            ),
                            html.Br(),
                            html.Label("Minimum operating capacity"),
                            dcc.Slider(
                                id="min-capacity-slider",
                                min=0,
                                max=100,
                                step=1,
                                value=int(min_operating_capacity*100),
                                marks={i: str(i) for i in range(0, 101, 10)},
                            ),
                        ]
                    ),
                    dbc.CardFooter(id='footer'),

                ], style={
                    "margin": "0px", "display": "flex", "flex-direction": "column"
                }),
        ], className="m-2 col-3"),

    ]),
    style={'overflow-y': 'auto', 'overflow-x': 'hidden'}  # Align elements vertically
)

dashapp.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Unit Block Loading Prototype</title>
        {%favicon%}
        {%css%}
    </head>
    <body style="margin: 0px; padding: 0px; overflow-y: hidden; overflow-x: hidden" >
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

input_components = [
    "days-slider",
    "generators-slider",
    "target-60-slider",
    "target-100-slider",
    "block-limit-slider",
    "min-capacity-slider",
]


@dashapp.callback(
    [
        Output("my-graph", "figure"),
        Output("footer", "children"),
    ],
    [
        Input(c, "value") for c in input_components
    ],
    prevent_initial_callbacks=True
)
def update_figure(days_, generators_, target_60_, target_100_, block_limit_, min_operating_capacity_):
    ctx = dash.callback_context
    triggered_item = ctx.triggered[0]["prop_id"].split(".")[0]
    if triggered_item in input_components:
        try:
            decision_fig, cumulative_cost_fig, active_power_fig, subplot_fig = run_basic_example(
                t=48 * days_, n=generators_, restart_targets=((target_60_, 0.6), (target_100_, 1)),
                block_limit=block_limit_,
                min_operating_capacity=min_operating_capacity_/100
            )
        except exceptions.InfeasibleSolutionException as e:
            return dash.no_update, "Infeasible Solution"
        return subplot_fig, ""
    return dash.no_update, ""


dashapp.title = 'Unit Block Loading'
app = dashapp.server
