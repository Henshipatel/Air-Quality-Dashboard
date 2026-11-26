import streamlit as st
import pandas as pd
import plotly.express as px
from scipy import stats

# ==========================================
# PAGE SETTINGS
# ==========================================

st.set_page_config(
    page_title="Air Quality & Weather Dashboard",
    page_icon="🌍",
    layout="wide"
)

# ==========================================
# PROFESSIONAL BLUE-WHITE DESIGN
# ==========================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #EAF4FF, #DCEBFA);
}

/* Main layout */
.block-container {
    padding: 2rem 2.5rem;
    max-width: 1500px;
}

/* Headings */
h1 {
    color: #12345A !important;
    font-weight: 800 !important;
}

h2 {
    color: #174A7E !important;
    font-weight: 700 !important;
}

h3 {
    color: #174A7E !important;
    font-weight: 650 !important;
}

/* All normal text */
p, label, li, .stMarkdown, .stCaption {
    color: #172B4D;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #E7F0FA;
    border-right: 1px solid #D3E1F0;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span {
    color: #12345A !important;
}

/* Metric Cards */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #DCE6F2;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 3px 12px rgba(18, 52, 90, 0.07);
}

div[data-testid="stMetricLabel"] {
    color: #425873 !important;
}

div[data-testid="stMetricValue"] {
    color: #12345A !important;
    font-weight: 800 !important;
}

/* Input labels */
.stSelectbox label,
.stDateInput label {
    color: #12345A !important;
    font-weight: 600 !important;
}

/* Buttons */
.stDownloadButton button {
    background-color: #1769AA;
    color: white !important;
    border-radius: 8px;
    border: none;
    font-weight: 600;
}

.stDownloadButton button:hover {
    background-color: #104C82;
}

/* Tables */
div[data-testid="stDataFrame"] {
    border: 1px solid #DCE6F2;
    border-radius: 10px;
}

/* Dividers */
hr {
    border-color: #D5E1EF;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# LOAD DATA
# ==========================================

@st.cache_data
def load_data():

    weather = pd.read_csv("weather_daily.csv")
    air = pd.read_csv("air_quality_daily.csv")
    cities = pd.read_csv("cities.csv")

    weather["date"] = pd.to_datetime(weather["date"])
    air["date"] = pd.to_datetime(air["date"])

    df = pd.merge(
        weather,
        air,
        on=["date", "city"],
        how="inner"
    )

    df = pd.merge(
        df,
        cities,
        on="city",
        how="left"
    )

    df = df.drop_duplicates(
        subset=["date", "city"]
    )

    if "india_aqi_pm" in df.columns:
        df["AQI"] = df["india_aqi_pm"]
    else:
        df["AQI"] = df["india_aqi"]

    if "india_aqi_pm_category" in df.columns:
        df["AQI Category"] = df["india_aqi_pm_category"]
    else:
        df["AQI Category"] = df["india_aqi_category"]

    df["Season"] = df["date"].dt.month.map({
        12: "Winter",
        1: "Winter",
        2: "Winter",
        3: "Summer",
        4: "Summer",
        5: "Summer",
        6: "Monsoon",
        7: "Monsoon",
        8: "Monsoon",
        9: "Monsoon",
        10: "Post-Monsoon",
        11: "Post-Monsoon"
    })

    return df


try:
    df = load_data()

except Exception as e:
    st.error("Data load nahi ho paya. CSV files check karo.")
    st.exception(e)
    st.stop()


# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("🌍 AQ Dashboard")
st.sidebar.markdown("Air Quality & Weather")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "🏠 Home",
        "🌫️ Air Quality Analysis",
        "🌡️ Weather Analysis",
        "🔗 Correlation Analysis",
        "🍃 Seasonal Analysis",
        "📊 Outlier Detection",
        "📈 Statistical Testing",
        "📁 Data Cleaning",
        "⏳ Lagged Correlation"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("FILTER DATA")

city_list = ["All Cities"] + sorted(
    df["city"].dropna().unique().tolist()
)

selected_city = st.sidebar.selectbox(
    "Select City",
    city_list
)

min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

filtered_df = df.copy()

if selected_city != "All Cities":
    filtered_df = filtered_df[
        filtered_df["city"] == selected_city
    ]

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df["date"].dt.date >= date_range[0]) &
        (filtered_df["date"].dt.date <= date_range[1])
    ]


# ==========================================
# CHART FUNCTION
# ==========================================

def show_chart(fig):

    fig.update_layout(
        font=dict(
            family="Arial",
            size=14,
            color="#172B4D"
        ),
        title_font=dict(
            size=21,
            color="#12345A"
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=30, r=30, t=65, b=30),
        legend_title_text=""
    )

    fig.update_xaxes(
        title_font=dict(color="#172B4D"),
        tickfont=dict(color="#172B4D"),
        showgrid=False
    )

    fig.update_yaxes(
        title_font=dict(color="#172B4D"),
        tickfont=dict(color="#172B4D"),
        gridcolor="#E5ECF5"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# EMPTY DATA CHECK
# ==========================================

if filtered_df.empty:

    st.warning("Selected filters ke liye data available nahi hai.")
    st.stop()


# ==========================================
# HOME PAGE
# ==========================================

if page == "🏠 Home":

    st.title("🌍 Air Quality & Weather Dashboard")

    st.markdown(
        "Monitor air pollution and understand its relationship with weather."
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Records",
        f"{len(filtered_df):,}"
    )

    col2.metric(
        "Average AQI",
        f"{filtered_df['AQI'].mean():.1f}"
    )

    col3.metric(
        "Average Temperature",
        f"{filtered_df['temperature_2m_mean'].mean():.1f} °C"
    )

    col4.metric(
        "Total Cities",
        filtered_df["city"].nunique()
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("AQI Category Distribution")

        category = (
            filtered_df["AQI Category"]
            .value_counts()
            .reset_index()
        )

        category.columns = ["Category", "Count"]

        fig = px.pie(
            category,
            names="Category",
            values="Count",
            hole=0.5,
            title="Air Quality Categories"
        )

        show_chart(fig)

    with col2:

        st.subheader("Daily AQI Trend")

        daily = (
            filtered_df.groupby("date")["AQI"]
            .mean()
            .reset_index()
        )

        fig = px.line(
            daily,
            x="date",
            y="AQI",
            markers=True,
            title="Average AQI Over Time"
        )

        fig.update_traces(line=dict(width=3))

        show_chart(fig)

    st.divider()

    st.subheader("City-wise Average AQI")

    city_data = (
        filtered_df.groupby("city")["AQI"]
        .mean()
        .reset_index()
        .sort_values("AQI", ascending=False)
    )

    fig = px.bar(
        city_data,
        x="city",
        y="AQI",
        color="AQI",
        color_continuous_scale="Blues",
        title="Average AQI by City"
    )

    show_chart(fig)


# ==========================================
# AIR QUALITY ANALYSIS
# ==========================================

elif page == "🌫️ Air Quality Analysis":

    st.title("🌫️ Air Quality Analysis")

    st.markdown("Explore pollution levels and pollutant trends.")

    col1, col2, col3 = st.columns(3)

    col1.metric("Average AQI", f"{filtered_df['AQI'].mean():.2f}")
    col2.metric("Maximum AQI", f"{filtered_df['AQI'].max():.2f}")
    col3.metric("Minimum AQI", f"{filtered_df['AQI'].min():.2f}")

    st.divider()

    pollutants = [
        "pm2_5_mean",
        "pm10_mean",
        "no2_mean",
        "so2_mean",
        "dust_mean",
        "aod_mean"
    ]

    available = [
        x for x in pollutants
        if x in filtered_df.columns
    ]

    pollutant = st.selectbox(
        "Select Pollutant",
        available
    )

    fig = px.line(
        filtered_df,
        x="date",
        y=pollutant,
        color="city" if selected_city == "All Cities" else None,
        title=f"{pollutant.upper()} Trend"
    )

    show_chart(fig)

    st.subheader("Pollutant Statistics")

    st.dataframe(
        filtered_df[available].describe().round(2),
        use_container_width=True
    )


# ==========================================
# WEATHER ANALYSIS
# ==========================================

elif page == "🌡️ Weather Analysis":

    st.title("🌡️ Weather Analysis")

    st.markdown("Understand weather patterns and their changes.")

    weather_columns = [
        "temperature_2m_mean",
        "temperature_2m_max",
        "temperature_2m_min",
        "relative_humidity_2m_mean",
        "wind_speed_10m_max",
        "precipitation_sum"
    ]

    available = [
        x for x in weather_columns
        if x in filtered_df.columns
    ]

    selected_weather = st.selectbox(
        "Select Weather Parameter",
        available
    )

    fig = px.line(
        filtered_df,
        x="date",
        y=selected_weather,
        color="city" if selected_city == "All Cities" else None,
        title=selected_weather.replace("_", " ").title()
    )

    show_chart(fig)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        fig = px.scatter(
            filtered_df,
            x="temperature_2m_mean",
            y="AQI",
            title="Temperature vs AQI",
            color="AQI",
            color_continuous_scale="Blues"
        )

        show_chart(fig)

    with col2:

        fig = px.scatter(
            filtered_df,
            x="relative_humidity_2m_mean",
            y="AQI",
            title="Humidity vs AQI",
            color="AQI",
            color_continuous_scale="Blues"
        )

        show_chart(fig)

    st.subheader("Temperature vs PM2.5")

    fig = px.scatter(
        filtered_df,
        x="temperature_2m_mean",
        y="pm2_5_mean",
        title="Temperature vs PM2.5",
        color="pm2_5_mean",
        color_continuous_scale="Blues"
    )

    show_chart(fig)


# ==========================================
# CORRELATION ANALYSIS
# ==========================================

elif page == "🔗 Correlation Analysis":

    st.title("🔗 Correlation Analysis")

    st.markdown(
        "Study relationships between weather and air pollution."
    )

    variables = [
        "AQI",
        "pm2_5_mean",
        "pm10_mean",
        "no2_mean",
        "so2_mean",
        "temperature_2m_mean",
        "relative_humidity_2m_mean",
        "wind_speed_10m_max",
        "precipitation_sum"
    ]

    available = [
        x for x in variables
        if x in filtered_df.columns
    ]

    pearson = filtered_df[available].corr(
        method="pearson"
    )

    spearman = filtered_df[available].corr(
        method="spearman"
    )

    st.subheader("Pearson Correlation Matrix")

    fig = px.imshow(
        pearson,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Pearson Correlation"
    )

    show_chart(fig)

    st.divider()

    st.subheader("Spearman Correlation Matrix")

    fig = px.imshow(
        spearman,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Spearman Correlation"
    )

    show_chart(fig)

    st.info(
        "Pearson measures linear relationships. "
        "Spearman measures rank-based monotonic relationships. "
        "Correlation does not prove causation."
    )


# ==========================================
# SEASONAL ANALYSIS
# ==========================================

elif page == "🍃 Seasonal Analysis":

    st.title("🍃 Seasonal Analysis")

    st.markdown("Compare air quality across different seasons.")

    seasonal = (
        filtered_df.groupby("Season", observed=True)["AQI"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )

    st.subheader("Seasonal AQI Summary")

    st.dataframe(
        seasonal.round(2),
        use_container_width=True
    )

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(
            seasonal,
            x="Season",
            y="mean",
            color="mean",
            title="Average AQI by Season",
            color_continuous_scale="Blues"
        )

        show_chart(fig)

    with col2:

        fig = px.box(
            filtered_df,
            x="Season",
            y="AQI",
            color="Season",
            title="Seasonal AQI Distribution"
        )

        show_chart(fig)

    st.divider()

    if filtered_df["Season"].nunique() >= 2:

        groups = [
            group["AQI"].dropna()
            for _, group in filtered_df.groupby("Season")
        ]

        groups = [g for g in groups if len(g) > 0]

        if len(groups) >= 2:

            h_stat, p_value = stats.kruskal(*groups)

            st.subheader("Kruskal-Wallis Statistical Test")

            col1, col2 = st.columns(2)

            col1.metric("H Statistic", f"{h_stat:.3f}")
            col2.metric("P Value", f"{p_value:.5f}")

            if p_value < 0.05:
                st.success(
                    "AQI differences between seasons are statistically significant."
                )
            else:
                st.info(
                    "No statistically significant seasonal difference was detected."
                )


# ==========================================
# OUTLIER DETECTION
# ==========================================

elif page == "📊 Outlier Detection":

    st.title("📊 Outlier Detection")

    st.markdown("Identify unusual AQI values using the IQR method.")

    aq = filtered_df["AQI"].dropna()

    q1 = aq.quantile(0.25)
    q3 = aq.quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = filtered_df[
        (filtered_df["AQI"] < lower) |
        (filtered_df["AQI"] > upper)
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric("Lower Limit", f"{lower:.2f}")
    col2.metric("Upper Limit", f"{upper:.2f}")
    col3.metric("Total Outliers", f"{len(outliers):,}")

    st.divider()

    fig = px.box(
        filtered_df,
        y="AQI",
        title="AQI Box Plot",
        color_discrete_sequence=["#2878B5"]
    )

    show_chart(fig)

    st.subheader("Outlier Records")

    st.dataframe(
        outliers[["date", "city", "AQI"]].head(100),
        use_container_width=True
    )


# ==========================================
# STATISTICAL TESTING
# ==========================================

elif page == "📈 Statistical Testing":

    st.title("📈 Statistical Testing")

    st.markdown("Descriptive statistics and AQI distribution.")

    aq = filtered_df["AQI"].dropna()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Mean", f"{aq.mean():.2f}")
    col2.metric("Median", f"{aq.median():.2f}")
    col3.metric(
        "Mode",
        f"{aq.mode().iloc[0]:.2f}" if not aq.mode().empty else "N/A"
    )
    col4.metric("Std Deviation", f"{aq.std():.2f}")

    st.divider()

    st.subheader("Complete Descriptive Statistics")

    st.dataframe(
        filtered_df.select_dtypes(include="number").describe().round(2),
        use_container_width=True
    )

    st.subheader("AQI Distribution")

    fig = px.histogram(
        filtered_df,
        x="AQI",
        nbins=40,
        title="AQI Frequency Distribution",
        color_discrete_sequence=["#2878B5"]
    )

    show_chart(fig)

    st.write("AQI Skewness:", round(aq.skew(), 3))


# ==========================================
# DATA CLEANING
# ==========================================

elif page == "📁 Data Cleaning":

    st.title("📁 Data Cleaning")

    st.markdown("Check missing values and duplicate records.")

    col1, col2 = st.columns(2)

    col1.metric(
        "Total Missing Values",
        f"{filtered_df.isnull().sum().sum():,}"
    )

    col2.metric(
        "Duplicate Records",
        f"{filtered_df.duplicated().sum():,}"
    )

    st.divider()

    st.subheader("Missing Values by Column")

    missing = (
        filtered_df.isnull()
        .sum()
        .reset_index()
    )

    missing.columns = ["Column", "Missing Values"]

    st.dataframe(
        missing,
        use_container_width=True
    )

    st.subheader("Cleaned Data Preview")

    cleaned_df = filtered_df.drop_duplicates().copy()

    st.dataframe(
        cleaned_df.head(100),
        use_container_width=True
    )

    csv = cleaned_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Cleaned Dataset",
        data=csv,
        file_name="cleaned_air_quality_data.csv",
        mime="text/csv"
    )


# ==========================================
# LAGGED CORRELATION
# ==========================================

elif page == "⏳ Lagged Correlation":

    st.title("⏳ Lagged Correlation Analysis")

    st.markdown(
        "Study whether previous-day weather conditions are related "
        "to today's air quality."
    )

    lag_data = filtered_df.sort_values(
        ["city", "date"]
    ).copy()

    lag_data["Previous Day Temperature"] = (
        lag_data.groupby("city")["temperature_2m_mean"].shift(1)
    )

    lag_data["Previous Day Humidity"] = (
        lag_data.groupby("city")["relative_humidity_2m_mean"].shift(1)
    )

    lag_data = lag_data.dropna(
        subset=[
            "Previous Day Temperature",
            "Previous Day Humidity",
            "AQI"
        ]
    )

    if len(lag_data) > 2:

        col1, col2 = st.columns(2)

        temp_corr = lag_data[
            "Previous Day Temperature"
        ].corr(lag_data["AQI"])

        humidity_corr = lag_data[
            "Previous Day Humidity"
        ].corr(lag_data["AQI"])

        col1.metric(
            "Previous Day Temperature vs AQI",
            f"{temp_corr:.3f}"
        )

        col2.metric(
            "Previous Day Humidity vs AQI",
            f"{humidity_corr:.3f}"
        )

        st.divider()

        fig = px.scatter(
            lag_data,
            x="Previous Day Temperature",
            y="AQI",
            title="Previous Day Temperature vs Today's AQI",
            color="AQI",
            color_continuous_scale="Blues"
        )

        show_chart(fig)

        fig = px.scatter(
            lag_data,
            x="Previous Day Humidity",
            y="AQI",
            title="Previous Day Humidity vs Today's AQI",
            color="AQI",
            color_continuous_scale="Blues"
        )

        show_chart(fig)

    else:

        st.warning(
            "Lagged analysis ke liye sufficient data available nahi hai."
        )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#425873;
        padding:15px;
        font-size:14px;
    ">
        <b>Air Quality & Weather Correlation Dashboard</b><br>
        Built with Python | Streamlit | Pandas | Plotly
    </div>
    """,
    unsafe_allow_html=True
)