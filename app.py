import streamlit as st
from datetime import datetime
from pension import Pension
import pandas as pd
import plotly.graph_objects as go

# Page configuration
st.set_page_config(page_title="Glidepath Simulator", page_icon="📈", layout="wide")

st.title("📈 Pension Glidepath Simulator")
st.markdown("Adjust the parameters to model how de-risking strategies affect the outcome of a pension pot")

# Use columns for a cleaner layout
col1, col2 = st.columns(2)

with col1:
    # Numeric inputs as integers
    contributions = st.number_input(
        "Monthly contribution",
        min_value=0,
        value=500,
        max_value=5000,
        step=50
    )

    derisking_years = st.number_input(
        "Derisking Years (years before retirement)",
        min_value=0,
        value=15,
        step=1
    )

with col2:
    # Date inputs
    start_date = st.date_input("Start Date", value=datetime(1990, 1, 1))
    start_date = pd.to_datetime(start_date)
    retirement_date = st.date_input("Retirement Date", value=datetime(2023, 1, 1))
    retirement_date = pd.to_datetime(retirement_date)


# Logic and Calculations
if start_date >= retirement_date:
    st.error("Error: Retirement date must be after the start date.")

# read in fund data
fund_data = pd.read_csv("fund_data.csv")

# initialise pension object
pension = Pension(start_date, retirement_date, contributions)

# load fund data
pension.load_data(fund_data)

# set derisking strategy
pension.derisk_strategy(0.2, derisking_years)

# accumulate pension
df_accum = pension.accumulate()

# calculate the different outputs
ending_value = round(df_accum.tail(1)["portfolio_value"].item())
total_cont = round(df_accum["cont"].sum())
return_perc = ((round(ending_value / total_cont, 4)) - 1) * 100

# create layout for the headline figures and graph
col1, col2 = st.columns([1, 2])

with col1:
    st.metric("Pension pot end value: ", ending_value)
    st.metric("Total contributions: ", total_cont)
    st.metric("Return as percentage: ", return_perc)

with col2:

    fig = go.Figure()

    # Add Portfolio Value Line
    fig.add_trace(go.Scatter(
        x=df_accum["date"],
        y=df_accum["portfolio_value"],
        mode='lines',
        name='Total Portfolio Value',
        line=dict(color='#1f77b4', width=3)
    ))

    # Add target weight visualization on a secondary axis
    fig.add_trace(go.Scatter(
        x=df_accum["date"],
        y=df_accum["ety_target"],
        name='Equity Allocation %',
        line=dict(color='orange', dash='dot'),
        yaxis="y2"
    ))

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        xaxis_title="Date",

        # Primary Y-Axis (Portfolio Value)
        yaxis=dict(
            title="Value ($)",
            showgrid=False,  # This removes the horizontal lines
            zeroline=False  # Optional: removes the thicker line at y=0
        ),

        # Secondary Y-Axis (Bond Weight)
        yaxis2=dict(
            title="Bond Weight (%)",
            overlaying="y",
            side="right",
            range=[0, 1],
            showgrid=False,  # Ensures no secondary grid lines appear
            zeroline=False
        ),

        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)