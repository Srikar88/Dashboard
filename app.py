import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from datetime import datetime

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Indian Stock Dashboard",
    page_icon="📈",
    layout="wide"
)

# ---------------------------------------------------
# F&O STOCK LIST
# ---------------------------------------------------

FNO_STOCKS = sorted([
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK",
    "SBIN","LT","AXISBANK","KOTAKBANK","ITC",
    "BHARTIARTL","ASIANPAINT","MARUTI","SUNPHARMA",
    "TITAN","ULTRACEMCO","BAJFINANCE","HCLTECH",
    "WIPRO","ONGC","POWERGRID","NTPC","TATAMOTORS",
    "M&M","INDUSINDBK","ADANIENT","ADANIPORTS",
    "JSWSTEEL","HINDALCO","COALINDIA","BPCL",
    "DIVISLAB","TECHM","GRASIM","EICHERMOT",
    "BAJAJFINSV","BAJAJ-AUTO","DRREDDY","CIPLA",
    "HEROMOTOCO","UPL","TATASTEEL","SBILIFE",
    "BRITANNIA","NESTLEIND","HDFCLIFE","APOLLOHOSP",
    "PIDILITIND","DABUR","AMBUJACEM"
])

MONTHS = [
    "Jan","Feb","Mar","Apr","May","Jun",
    "Jul","Aug","Sep","Oct","Nov","Dec"
]

# ---------------------------------------------------
# SYMBOL FORMATTER
# ---------------------------------------------------

def normalize_symbol(symbol):

    symbol = symbol.strip().upper()

    index_map = {
        "NIFTY50": "^NSEI",
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "FINNIFTY": "^CNXFINSERVICE",
    }

    if symbol in index_map:
        return index_map[symbol]

    if not symbol.endswith(".NS"):
        symbol = symbol + ".NS"

    return symbol

# ---------------------------------------------------
# FETCH DATA
# ---------------------------------------------------

@st.cache_data(ttl=3600)
def fetch_data(symbol):

    try:

        df = yf.download(
            symbol,
            period="15y",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            return None

        df = df.dropna()

        return df

    except Exception:
        return None

# ---------------------------------------------------
# MONTHLY RETURNS MATRIX
# ---------------------------------------------------

def create_monthly_matrix(df):

    monthly_close = df["Close"].resample("ME").last()

    monthly_returns = monthly_close.pct_change() * 100

    monthly_df = pd.DataFrame(monthly_returns)

    monthly_df.columns = ["Return"]

    monthly_df["Year"] = monthly_df.index.year
    monthly_df["Month"] = monthly_df.index.month

    # last 10 years ONLY
    current_year = datetime.now().year

    years = list(range(current_year - 9, current_year + 1))

    matrix = monthly_df.pivot_table(
        index="Year",
        columns="Month",
        values="Return"
    )

    matrix = matrix.reindex(years)

    matrix = matrix.reindex(columns=range(1, 13))

    matrix.columns = MONTHS

    # yearly returns
    yearly_returns = {}

    for year in years:

        yearly_data = monthly_close[
            monthly_close.index.year == year
        ]

        if len(yearly_data) > 1:

            start_price = yearly_data.iloc[0]
            end_price = yearly_data.iloc[-1]

            yearly_return = (
                (end_price / start_price) - 1
            ) * 100

            yearly_returns[year] = round(yearly_return, 2)

        else:
            yearly_returns[year] = np.nan

    matrix["Yearly"] = pd.Series(yearly_returns)

    return matrix.round(2)

# ---------------------------------------------------
# STATS
# ---------------------------------------------------

def calculate_stats(df):

    daily_returns = df["Close"].pct_change().dropna()

    total_years = len(df) / 252

    cagr = (
        (
            df["Close"].iloc[-1]
            / df["Close"].iloc[0]
        ) ** (1 / total_years) - 1
    ) * 100

    volatility = (
        daily_returns.std()
        * np.sqrt(252)
        * 100
    )

    rolling_max = df["Close"].cummax()

    drawdown = (
        df["Close"] / rolling_max - 1
    )

    max_drawdown = drawdown.min() * 100

    return {
        "CAGR": round(cagr, 2),
        "Volatility": round(volatility, 2),
        "Max Drawdown": round(max_drawdown, 2)
    }

# ---------------------------------------------------
# EXCEL EXPORT
# ---------------------------------------------------

def export_excel(data):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        for symbol, matrix in data.items():

            matrix.to_excel(
                writer,
                sheet_name=symbol[:30]
            )

    output.seek(0)

    return output

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.title("📊 Controls")

selected_stock = st.sidebar.selectbox(
    "Select F&O Stock",
    FNO_STOCKS
)

custom_stock = st.sidebar.text_input(
    "Or Enter Symbol"
)

if custom_stock:
    symbol = normalize_symbol(custom_stock)
else:
    symbol = normalize_symbol(selected_stock)

show_heatmap = st.sidebar.checkbox(
    "Show Heatmap",
    value=True
)

show_candle = st.sidebar.checkbox(
    "Show Candlestick Chart",
    value=True
)

show_drawdown = st.sidebar.checkbox(
    "Show Drawdown",
    value=True
)

show_rolling = st.sidebar.checkbox(
    "Show Rolling Returns",
    value=True
)

# ---------------------------------------------------
# TITLE
# ---------------------------------------------------

st.title("📈 Indian Futures Dashboard")

st.markdown("""
Monthly seasonality + technical analysis dashboard
for Indian futures stocks and indices.
""")

# ---------------------------------------------------
# DATA
# ---------------------------------------------------

df = fetch_data(symbol)

if df is None:

    st.error(
        f"No data found for {symbol}"
    )

    st.stop()

# ---------------------------------------------------
# MATRIX
# ---------------------------------------------------

matrix = create_monthly_matrix(df)

# ---------------------------------------------------
# METRICS
# ---------------------------------------------------

stats = calculate_stats(df)

c1, c2, c3 = st.columns(3)

c1.metric(
    "CAGR",
    f"{stats['CAGR']}%"
)

c2.metric(
    "Volatility",
    f"{stats['Volatility']}%"
)

c3.metric(
    "Max Drawdown",
    f"{stats['Max Drawdown']}%"
)

# ---------------------------------------------------
# HEATMAP
# ---------------------------------------------------

if show_heatmap:

    st.subheader("📅 Monthly Returns Heatmap")

    heatmap_data = matrix.drop(
        columns=["Yearly"]
    )

    fig_heat = px.imshow(
        heatmap_data,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdYlGn"
    )

    fig_heat.update_layout(
        height=650
    )

    st.plotly_chart(
        fig_heat,
        use_container_width=True
    )

# ---------------------------------------------------
# MATRIX TABLE
# ---------------------------------------------------

st.subheader("📊 Monthly Returns Matrix")

st.dataframe(
    matrix,
    use_container_width=True,
    height=500
)

# ---------------------------------------------------
# CANDLESTICK CHART
# ---------------------------------------------------

if show_candle:

    st.subheader("🕯️ Candlestick Chart")

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"]
            )
        ]
    )

    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ---------------------------------------------------
# DRAWDOWN
# ---------------------------------------------------

if show_drawdown:

    st.subheader("📉 Drawdown")

    rolling_max = df["Close"].cummax()

    drawdown = (
        df["Close"] / rolling_max - 1
    ) * 100

    fig_dd = go.Figure()

    fig_dd.add_trace(
        go.Scatter(
            x=df.index,
            y=drawdown,
            fill="tozeroy",
            name="Drawdown"
        )
    )

    fig_dd.update_layout(
        height=400
    )

    st.plotly_chart(
        fig_dd,
        use_container_width=True
    )

# ---------------------------------------------------
# ROLLING RETURNS
# ---------------------------------------------------

if show_rolling:

    st.subheader("📈 Rolling 1Y Returns")

    rolling = (
        df["Close"].pct_change(252)
    ) * 100

    fig_roll = go.Figure()

    fig_roll.add_trace(
        go.Scatter(
            x=rolling.index,
            y=rolling,
            mode="lines",
            name="Rolling Returns"
        )
    )

    fig_roll.update_layout(
        height=400
    )

    st.plotly_chart(
        fig_roll,
        use_container_width=True
    )

# ---------------------------------------------------
# EXCEL DOWNLOAD
# ---------------------------------------------------

excel_file = export_excel({
    symbol: matrix
})

st.download_button(
    label="📥 Download Excel",
    data=excel_file,
    file_name=f"{symbol}_monthly_returns.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------

st.markdown("---")

st.caption(
    "Indian Stock Futures Dashboard • Streamlit"
)
