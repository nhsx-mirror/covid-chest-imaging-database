import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output
from flask_caching import Cache

from dataset import Dataset
from pages import tools
from pages.tools import numformat

cache = Cache(config={"CACHE_TYPE": "simple"})


# Caching is done so that when the dataset's values
# are updated, the page will pull in the updated values.
@cache.cached(timeout=180)
def serve_layout(data: Dataset) -> html.Div:
    """Create the page layout for the summary page

    Parameters
    ----------
    data : dataset.Dataset
        The main dataset which is used for analysis.

    Returns
    -------
    dash_html_components.Div
        The HTML componets of the page layout, wrapped in  div
    """

    dataset_select = dcc.Dropdown(
        options=[
            {"label": "All all data", "value": "all"},
            {"label": "Training set", "value": "training"},
            {"label": "Validation set", "value": "validation"},
        ],
        value="all",
        clearable=False,
        id="dataset-select",
    )

    covid_status_select = dcc.Dropdown(
        options=[
            {"label": "All patients", "value": "all"},
            {"label": "Positive patients", "value": "positive"},
            {"label": "Negative patients", "value": "negative"},
        ],
        value="all",
        clearable=False,
        id="covid-status-select",
    )

    selector = html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Label(
                                    [
                                        "Select dataset",
                                    ],
                                    htmlFor="dataset-select",
                                ),
                                dataset_select,
                            ]
                        ),
                        md=6,
                        sm=12,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Label(
                                    [
                                        "Select COVID-19 status",
                                    ],
                                    htmlFor="covid-status-select",
                                ),
                                covid_status_select,
                            ]
                        ),
                        md=6,
                        sm=12,
                    ),
                ]
            )
        ]
    )

    page = html.Div(
        children=[
            html.H1(children="Patients"),
            html.H2("Patients demographics breakdown"),
            html.H3("Gender"),
            create_gender_breakdown(data),
            html.Hr(),
            html.H3("Age and Ethnicity"),
            html.P(
                "Select dataset or COVID-19 status to filter the plots below."
            ),
            selector,
            dcc.Loading(
                id="loading-age-data",
                type="dot",
                color="black",
                children=html.Div(id="age-breakdown-plot"),
            ),
            dcc.Loading(
                id="loading-ethnicity-data",
                type="dot",
                color="black",
                children=html.Div(id="ethnicity-breakdown-plot"),
            ),
        ]
    )

    return page


def create_app(data: Dataset, **kwargs: str) -> dash.Dash:
    """Create a Dash app for the given page

    Parameters
    ----------
    data : dataset.Dataset
        Description of parameter `x`.
    **kwargs : dict
        Keyword arguments to pass on to the Dash app constructor.

    Returns
    -------
    dash.Dash
        The Dash app to display on the given page.
    """
    app = dash.Dash(__name__, **kwargs)
    cache.init_app(app.server)

    app.layout = lambda: serve_layout(data)

    @app.callback(
        Output("age-breakdown-plot", "children"),
        Input("dataset-select", "value"),
        Input("covid-status-select", "value"),
    )
    def set_age_breakdown(group, covid_status):
        return create_age_breakdown(data, group, covid_status)

    @app.callback(
        Output("ethnicity-breakdown-plot", "children"),
        Input("dataset-select", "value"),
        Input("covid-status-select", "value"),
    )
    def set_ethnicity_breakdown(group, covid_status):
        return create_ethnicity_breakdown(data, group, covid_status)

    return app


def create_age_breakdown(data, group, covid_status):
    patient = data.data["patient"]
    # Filter for group
    if group != "all":
        patient = patient[patient["group"] == group]
        title_group = f"{group.title()} set"
    else:
        title_group = "All data"

    # Filter for status
    if covid_status == "positive":
        patient = patient[patient["filename_covid_status"]]
        title_status = "Positive patients"
    elif covid_status == "negative":
        patient = patient[~patient["filename_covid_status"]]
        title_status = "Negative patients"
    else:
        title_status = "All patients"

    fig = px.histogram(
        patient,
        x="age_update",
        title=f"Age Distribution of Patients, {title_group}, {title_status}",
        labels={"age_update": "Age", "filename_covid_status": "Covid status"},
        #    color="group"
    )
    graph = dcc.Graph(id="age-histogram", figure=fig)
    return graph


def create_ethnicity_breakdown(data, group, covid_status):
    patient = data.data["patient"]
    # Filter for group
    if group != "all":
        patient = patient[patient["group"] == group]
        title_group = f"{group.title()} set"
    else:
        title_group = "All data"

    # Filter for status
    if covid_status == "positive":
        patient = patient[patient["filename_covid_status"]]
        title_status = "Positive patients"
    elif covid_status == "negative":
        patient = patient[~patient["filename_covid_status"]]
        title_status = "Negative patients"
    else:
        title_status = "All patients"

    ethnic_groups = ["Asian", "Black", "White", "Multiple", "Other", "Unknown"]
    fig = px.histogram(
        patient,
        x="ethnicity",
        title=f"Ethnicity Distribution of Patients, {title_group}, {title_status}",
        labels={"ethnicity": "Ethnicity"},
        category_orders={"ethnicity": ethnic_groups},
    )
    graph = dcc.Graph(id="ethnicity-histogram", figure=fig)
    return graph


def create_gender_breakdown(data):
    patient = data.data["patient"]
    total = patient["sex_update"].value_counts()
    training = patient[patient["group"] == "training"][
        "sex_update"
    ].value_counts()
    validation = patient[patient["group"] == "validation"][
        "sex_update"
    ].value_counts()
    n_patients = patient.count()

    # total_column = [f"{numformat(total['M'])} ({total['M']/n_patients:.1f}%)",
    #  f"{total['F']}", f"{total['Unknown']}", 0]

    def calculate_column(dataset):
        genders = ["M", "F", "Unknown"]
        num = sum([dataset[g] for g in genders])
        column = [
            "{} ({:.1%})".format(numformat(dataset[g]), dataset[g] / num)
            for g in genders
        ]
        n_mf = dataset["M"] + dataset["F"]
        column += [
            "{:d}:{:d}%".format(
                round(dataset["M"] / n_mf * 100),
                round(dataset["F"] / n_mf * 100),
            )
        ]
        return column

    gender = {
        "Gender": ["Male", "Female", "Unknown", "Male:Female ratio"],
        "Total": calculate_column(total),
        "Training set": calculate_column(training),
        "Validation set": calculate_column(validation),
    }

    df = pd.DataFrame(
        gender, columns=["Gender", "Total", "Training set", "Validation set"]
    )

    table = dbc.Table.from_dataframe(df)
    return table
