def create_monthly_matrix(df):

    monthly_close = df['Close'].resample('ME').last()

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

    matrix.columns = [
        'Jan', 'Feb', 'Mar', 'Apr',
        'May', 'Jun', 'Jul', 'Aug',
        'Sep', 'Oct', 'Nov', 'Dec'
    ]

    # Correct yearly returns
    yearly_returns = (
        monthly_close
        .groupby(monthly_close.index.year)
        .apply(
            lambda x: (
                (x.iloc[-1] / x.iloc[0]) - 1
            ) * 100
        )
    )

    matrix['Yearly'] = yearly_returns

    return matrix.round(2)
