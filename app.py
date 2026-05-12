import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Indian Stock Futures Dashboard",
    page_icon="📈",
    layout="wide"
)

# ---------------------------------------------------
# NSE F&O STOCK LIST
# ---------------------------------------------------

FNO_STOCKS = [
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
]

MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr',
    'May', 'Jun', 'Jul', 'Aug',
    'Sep', 'Oct', 'Nov', 'Dec'
]

# ---------------------------------------------------
# SYMBOL NORMALIZATION
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
# FETCH DATA
# ---------------------------------------------------

@st.cache_data
def fetch_data(symbol):

    try:

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period="max",
            auto_adjust=True
        )

        if df.empty:
            return None

        return df

    except:
        return None

# ---------------------------------------------------
# MONTHLY RETURNS MATRIX
# ---------------------------------------------------

def create_monthly_matrix(df):

    monthly_close = df['Close'].resample('M').last()

    monthly_returns = monthly_close.pct_change() * 100

    monthly_df = pd.DataFrame(monthly_returns)

    monthly_df.columns = ['Return']

    monthly_df['Year'] = monthly_df.index.year
    monthly_df['Month'] = monthly_df.index.month

    min_year = monthly_df['Year'].min()
    max_year = monthly_df['Year'].max()

    full_years = list(range(min_year, max_year + 1))

    matrix = monthly_df.pivot_table(
        index='Year',
        columns='Month',
        values='Return'
    )

    matrix = matrix.reindex(full_years)

    matrix = matrix.reindex(columns=range(1, 13))

    matrix.columns = MONTHS

    yearly_returns = (
        monthly_close.groupby(monthly_close.index.year)
        .apply(
            lambda x: (
                (x.iloc[-1] / x.iloc[0]) - 1
            ) * 100
        )
    )

    matrix['Yearly'] = yearly_returns

    return matrix.round(2)

# ---------------------------------------------------
# PERFORMANCE STATS
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

    volatility = (
        daily_returns.std() * np.sqrt(252)
    ) * 100

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
# EXCEL EXPORT
# ---------------------------------------------------

def generate_excel(data_dict):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine='xlsxwriter'
    ) as writer:

        for stock, matrix in data_dict.items():

            matrix.to_excel(
                writer,
                sheet_name=stock[:30]
            )

    output.seek(0)

    return output

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.title("📊 Dashboard Controls")

selected_stock = st.sidebar.selectbox(
    "Select NSE F&O Stock",
    FNO_STOCKS
)

custom_stock = st.sidebar.text_input(
    "Or Enter Custom Symbol"
)

if custom_stock:
    symbols = [normalize_symbol(custom_stock)]
else:
    symbols = [normalize_symbol(selected_stock)]

show_heatmap = st.sidebar.checkbox(
    "Show Heatmap",
    True
)

show_candlestick = st.sidebar.checkbox(
    "Show Candlestick Chart",
    True
)

show_drawdown = st.sidebar.checkbox(
    "Show Drawdown Chart",
    True
)

show_rolling = st.sidebar.checkbox(
    "Show Rolling Returns",
    True
)

# ---------------------------------------------------
# MAIN TITLE
# ---------------------------------------------------

st.title("📈 Indian Stock Futures Dashboard")

st.markdown("""
Comprehensive dashboard for:
- Monthly seasonality analysis
- Technical trend analysis
- Rolling returns
- Drawdowns
- Long-term price action
""")

all_data = {}

# ---------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------

for symbol in symbols:

    st.divider()

    st.header(symbol)

    df = fetch_data(symbol)

    if df is None:

        st.error(f"No data found for {symbol}")

        continue

    matrix = create_monthly_matrix(df)

    all_data[symbol] = matrix

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
            columns=['Yearly']
        )

        fig_heatmap = px.imshow(
            heatmap_data,
            text_auto=True,
            aspect='auto',
            color_continuous_scale='RdYlGn'
        )

        fig_heatmap.update_layout(
            height=700
        )

        st.plotly_chart(
            fig_heatmap,
            use_container_width=True
        )

    # ---------------------------------------------------
    # RETURNS MATRIX
    # ---------------------------------------------------

    st.subheader("📊 Monthly Returns Matrix")

    st.dataframe(
        matrix.style.background_gradient(
            cmap='RdYlGn',
            axis=None
        ),
        use_container_width=True,
        height=700
    )

    # ---------------------------------------------------
    # CANDLESTICK CHART
    # ---------------------------------------------------

    if show_candlestick:

        st.subheader("🕯️ Candlestick Chart")

        fig_candle = go.Figure(
            data=[
                go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close']
                )
            ]
        )

        fig_candle.update_layout(
            height=700,
            xaxis_rangeslider_visible=False
        )

        st.plotly_chart(
            fig_candle,
            use_container_width=True
        )

    # ---------------------------------------------------
    # DRAWDOWN CHART
    # ---------------------------------------------------

    if show_drawdown:

        st.subheader("📉 Drawdown Analysis")

        rolling_max = df['Close'].cummax()

        drawdown = (
            df['Close'] / rolling_max - 1
        ) * 100

        fig_drawdown = go.Figure()

        fig_drawdown.add_trace(
            go.Scatter(
                x=df.index,
                y=drawdown,
                fill='tozeroy',
                name='Drawdown %'
            )
        )

        fig_drawdown.update_layout(
            height=400,
            yaxis_title="Drawdown %",
            xaxis_title="Date"
        )

        st.plotly_chart(
            fig_drawdown,
            use_container_width=True
        )

    # ---------------------------------------------------
    # ROLLING RETURNS
    # ---------------------------------------------------

    if show_rolling:

        st.subheader("📈 Rolling 1-Year Returns")

        rolling_returns = (
            df['Close'].pct_change(252)
        ) * 100

        fig_roll = go.Figure()

        fig_roll.add_trace(
            go.Scatter(
                x=rolling_returns.index,
                y=rolling_returns,
                mode='lines',
                name='1Y Rolling Return'
            )
        )

        fig_roll.update_layout(
            height=400,
            yaxis_title="Return %",
            xaxis_title="Date"
        )

        st.plotly_chart(
            fig_roll,
            use_container_width=True
        )

# ---------------------------------------------------
# COMPARISON TABLE
# ---------------------------------------------------

if len(all_data) > 0:

    st.divider()

    st.header("📌 Stock Performance Comparison")

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
# DOWNLOAD EXCEL
# ---------------------------------------------------

if all_data:

    excel_data = generate_excel(all_data)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name=f"stock_dashboard_{datetime.now().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------

st.markdown("---")

st.caption(
    "Built with Streamlit • Indian Futures Market Dashboard"
)
