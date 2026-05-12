import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="Indian Stock Dashboard",
    page_icon="📈",
    layout="wide"
)

MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

# ---------------------------------------------------
# Symbol Formatter
# ---------------------------------------------------

def normalize_symbol(symbol):

    symbol = symbol.strip().upper()

    nifty_map = {
        "NIFTY50": "^NSEI",
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "FINNIFTY": "^CNXFINSERVICE",
        "MIDCPNIFTY": "^NSEMDCP50"
    }

    if symbol in nifty_map:
        return nifty_map[symbol]

    if ".NS" not in symbol and ".BO" not in symbol:
        symbol = symbol + ".NS"

    return symbol

# ---------------------------------------------------
# Fetch Data
# ---------------------------------------------------

@st.cache_data
def fetch_data(symbol):

    try:
        ticker = yf.Ticker(symbol)

        df = ticker.history(period="max", auto_adjust=True)

        if df.empty:
            return None

        return df[['Close']]

    except:
        return None

# ---------------------------------------------------
# Monthly Return Matrix
# ---------------------------------------------------

def create_monthly_matrix(df):

    monthly_prices = df['Close'].resample('M').last()

    monthly_returns = monthly_prices.pct_change() * 100

    monthly_df = monthly_returns.to_frame(name='Return')

    monthly_df['Year'] = monthly_df.index.year
    monthly_df['Month'] = monthly_df.index.month

    matrix = monthly_df.pivot_table(
        index='Year',
        columns='Month',
        values='Return'
    )

    matrix = matrix.reindex(columns=range(1, 13))

    matrix.columns = MONTHS

    # Correct yearly compounded returns
    yearly_returns = (
        monthly_prices.resample('Y').last().pct_change() * 100
    )

    yearly_returns.index = yearly_returns.index.year

    matrix['Yearly'] = yearly_returns

    return matrix.round(2)

# ---------------------------------------------------
# Statistics
# ---------------------------------------------------

def calculate_stats(df):

    daily_returns = df['Close'].pct_change().dropna()

    total_years = len(df) / 252

    cagr = (
        (
            df['Close'].iloc[-1] /
            df['Close'].iloc[0]
        ) ** (1 / total_years) - 1
    ) * 100

    volatility = daily_returns.std() * np.sqrt(252) * 100

    rolling_max = df['Close'].cummax()

    drawdown = (
        df['Close'] / rolling_max - 1
    )

    max_drawdown = drawdown.min() * 100

    return {
        "CAGR": round(cagr, 2),
        "Volatility": round(volatility, 2),
        "Max Drawdown": round(max_drawdown, 2)
    }

# ---------------------------------------------------
# Excel Export
# ---------------------------------------------------

def generate_excel(data_dict):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        for stock, matrix in data_dict.items():

            matrix.to_excel(writer, sheet_name=stock[:30])

    output.seek(0)

    return output

# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------

st.sidebar.title("📊 Dashboard Controls")

symbols_input = st.sidebar.text_area(
    "Enter Stocks / Indices",
    value="RELIANCE, TCS, INFY, NIFTY50"
)

show_heatmap = st.sidebar.checkbox("Show Heatmap", True)
show_line_chart = st.sidebar.checkbox("Show Price Chart", True)
show_drawdown = st.sidebar.checkbox("Show Drawdown", True)

symbols = [
    normalize_symbol(x)
    for x in symbols_input.split(",")
]

all_data = {}

# ---------------------------------------------------
# Main Dashboard
# ---------------------------------------------------

st.title("📈 Indian Stock Monthly Returns Dashboard")

for symbol in symbols:

    st.divider()

    st.header(symbol)

    df = fetch_data(symbol)

    if df is None:

        st.error(f"No data found for {symbol}")

        continue

    matrix = create_monthly_matrix(df)

    all_data[symbol] = matrix

    # --------------------------------------------
    # Statistics
    # --------------------------------------------

    stats = calculate_stats(df)

    c1, c2, c3 = st.columns(3)

    c1.metric("CAGR", f"{stats['CAGR']}%")
    c2.metric("Volatility", f"{stats['Volatility']}%")
    c3.metric("Max Drawdown", f"{stats['Max Drawdown']}%")

    # --------------------------------------------
    # Heatmap
    # --------------------------------------------

    if show_heatmap:

        st.subheader("Monthly Return Heatmap")

        heatmap_data = matrix.drop(columns=['Yearly'])

        fig = px.imshow(
            heatmap_data,
            text_auto=True,
            color_continuous_scale='RdYlGn',
            aspect='auto'
        )

        fig.update_layout(
            height=600
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------
    # Matrix Table
    # --------------------------------------------

    st.subheader("Monthly Returns Matrix")

    st.dataframe(
        matrix.style.background_gradient(
            cmap='RdYlGn',
            axis=None
        ),
        use_container_width=True,
        height=600
    )

    # --------------------------------------------
    # Price Chart
    # --------------------------------------------

    if show_line_chart:

        st.subheader("Price Trend")

        fig2 = go.Figure()

        fig2.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Close'],
                mode='lines',
                name=symbol
            )
        )

        fig2.update_layout(
            height=500,
            xaxis_title="Date",
            yaxis_title="Price"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    # --------------------------------------------
    # Drawdown Chart
    # --------------------------------------------

    if show_drawdown:

        st.subheader("Drawdown Chart")

        rolling_max = df['Close'].cummax()

        drawdown = (
            df['Close'] / rolling_max - 1
        ) * 100

        fig3 = go.Figure()

        fig3.add_trace(
            go.Scatter(
                x=df.index,
                y=drawdown,
                fill='tozeroy',
                name='Drawdown %'
            )
        )

        fig3.update_layout(
            height=400,
            yaxis_title="Drawdown %",
            xaxis_title="Date"
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )

# ---------------------------------------------------
# Comparison Table
# ---------------------------------------------------

if len(all_data) > 1:

    st.divider()

    st.header("📌 Stock Comparison")

    comparison = []

    for symbol in symbols:

        df = fetch_data(symbol)

        if df is not None:

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

# ---------------------------------------------------
# Excel Download
# ---------------------------------------------------

if all_data:

    excel_data = generate_excel(all_data)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name=f"stock_dashboard_{datetime.now().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
