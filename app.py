# app.py
# Indian Stock Monthly Returns Dashboard Web App
# Run:
# pip install streamlit yfinance pandas numpy plotly openpyxl xlsxwriter
# streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="Indian Stock Monthly Returns Dashboard",
    page_icon="📈",
    layout="wide"
)

# -----------------------------
# Helper Functions
# -----------------------------

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def normalize_symbol(symbol):
    symbol = symbol.strip().upper()

    if ".NS" not in symbol and ".BO" not in symbol:
        symbol = f"{symbol}.NS"

    return symbol


@st.cache_data
def fetch_data(symbol, period="12y"):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, auto_adjust=True)

    if df.empty:
        return None

    df = df[['Close']]
    return df


def create_monthly_returns(df):
    monthly = df['Close'].resample('ME').last().pct_change() * 100
    monthly = monthly.to_frame(name='Return')

    monthly['Year'] = monthly.index.year
    monthly['Month'] = monthly.index.month

    pivot = monthly.pivot_table(
        index='Year',
        columns='Month',
        values='Return'
    )

    pivot = pivot.reindex(columns=range(1, 13))
    pivot.columns = MONTHS

    yearly_returns = (
        df['Close']
        .resample('YE')
        .last()
        .pct_change() * 100
    )

    yearly_returns.index = yearly_returns.index.year

    pivot['Yearly'] = yearly_returns

    pivot = pivot.tail(10)

    return pivot.round(2)


def calculate_stats(df):
    daily_returns = df['Close'].pct_change().dropna()

    cagr = (
        (df['Close'].iloc[-1] / df['Close'].iloc[0])
        ** (252 / len(df)) - 1
    ) * 100

    volatility = daily_returns.std() * np.sqrt(252) * 100

    max_drawdown = (
        (df['Close'] / df['Close'].cummax()) - 1
    ).min() * 100

    monthly = df['Close'].resample('ME').last().pct_change() * 100

    best_month = monthly.max()
    worst_month = monthly.min()

    return {
        "CAGR": round(cagr, 2),
        "Volatility": round(volatility, 2),
        "Max Drawdown": round(max_drawdown, 2),
        "Best Month": round(best_month, 2),
        "Worst Month": round(worst_month, 2),
    }


def export_excel(data_dict):
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'align': 'center'
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#DCE6F1',
            'border': 1
        })

        for stock, df in data_dict.items():
            df.to_excel(writer, sheet_name=stock[:31])

            worksheet = writer.sheets[stock[:31]]

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num + 1, value, header_format)

            worksheet.set_column(0, 20, 12)

    output.seek(0)
    return output


# -----------------------------
# Sidebar
# -----------------------------

st.sidebar.title("📊 Dashboard Controls")

symbols_input = st.sidebar.text_area(
    "Enter Indian Stock Symbols",
    value="RELIANCE, TCS, INFY",
    help="Separate multiple stocks with commas"
)

show_heatmap = st.sidebar.checkbox("Show Heatmap", value=True)
show_price_chart = st.sidebar.checkbox("Show Price Chart", value=True)
show_stats = st.sidebar.checkbox("Show Statistics", value=True)

# -----------------------------
# Main Title
# -----------------------------

st.title("📈 Indian Stock Monthly Returns Dashboard")
st.markdown(
    "Matrix view of monthly returns for the last 10 years."
)

symbols = [
    normalize_symbol(x)
    for x in symbols_input.split(",")
    if x.strip()
]

all_data = {}

# -----------------------------
# Process Each Stock
# -----------------------------

for symbol in symbols:

    st.divider()

    st.subheader(f"Stock: {symbol}")

    df = fetch_data(symbol)

    if df is None:
        st.error(f"Unable to fetch data for {symbol}")
        continue

    matrix = create_monthly_returns(df)

    all_data[symbol] = matrix

    # -----------------------------
    # Metrics
    # -----------------------------

    if show_stats:
        stats = calculate_stats(df)

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("CAGR", f"{stats['CAGR']}%")
        col2.metric("Volatility", f"{stats['Volatility']}%")
        col3.metric("Max Drawdown", f"{stats['Max Drawdown']}%")
        col4.metric("Best Month", f"{stats['Best Month']}%")
        col5.metric("Worst Month", f"{stats['Worst Month']}%")

    # -----------------------------
    # Heatmap
    # -----------------------------

    if show_heatmap:

        heatmap_data = matrix.drop(columns=['Yearly'])

        fig = px.imshow(
            heatmap_data,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdYlGn",
            labels=dict(color="Monthly Return %")
        )

        fig.update_layout(
            height=500,
            xaxis_title="Month",
            yaxis_title="Year"
        )

        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Data Table
    # -----------------------------

    st.markdown("### Monthly Returns Matrix")

    styled = matrix.style.background_gradient(
        cmap='RdYlGn',
        axis=None
    )

    st.dataframe(
        styled,
        use_container_width=True,
        height=450
    )

    # -----------------------------
    # Price Chart
    # -----------------------------

    if show_price_chart:

        fig_price = go.Figure()

        fig_price.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Close'],
                mode='lines',
                name=symbol
            )
        )

        fig_price.update_layout(
            title=f"{symbol} Price Trend",
            xaxis_title="Date",
            yaxis_title="Price",
            height=450
        )

        st.plotly_chart(fig_price, use_container_width=True)

# -----------------------------
# Comparison Section
# -----------------------------

if len(all_data) > 1:

    st.divider()
    st.header("📌 Stock Comparison")

    comparison = []

    for symbol in symbols:

        df = fetch_data(symbol)

        if df is None:
            continue

        stats = calculate_stats(df)

        comparison.append({
            "Stock": symbol,
            **stats
        })

    comparison_df = pd.DataFrame(comparison)

    st.dataframe(
        comparison_df,
        use_container_width=True
    )

# -----------------------------
# Excel Export
# -----------------------------

if all_data:

    excel_file = export_excel(all_data)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_file,
        file_name=f"monthly_returns_dashboard_{datetime.now().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -----------------------------
# Footer
# -----------------------------

st.markdown("---")
st.caption("Built with Streamlit • NSE/BSE Monthly Returns Dashboard")
