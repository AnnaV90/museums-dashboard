# streamlit_app.py
import streamlit as st
import pandas as pd
from main import get_museum_dataframe, make_predictions  # import your helper functions
import altair as alt

st.set_page_config(page_title="Museums Dashboard", layout="wide")
st.title("Museums Visitors & City Population Dashboard")

# 1️⃣ Show the full dataframe
st.header("Museums Table with Population")
df = get_museum_dataframe()
st.dataframe(df)  # interactive table

# 2️⃣ Input for custom population predictions
st.header("Predict Visitors by City Population")
user_input = st.text_input(
    "Enter populations separated by commas (e.g., 1000000,5000000,10000000):",
    "1000000,5000000,10000000"
)

if st.button("Predict"):
    try:
        # Make predictions
        results = make_predictions(df, user_input)

        # Display numeric results
        st.subheader("Prediction Summary")
        pops_list = [int(p.strip()) for p in user_input.split(",")]

        # Create a summary DataFrame
        summary_df = pd.DataFrame({
            "City Population": pops_list,
            "Predicted Visitors": results["predictions"]
        })

        # Format numbers with commas
        summary_df["City Population"] = summary_df["City Population"].apply(lambda x: f"{x:,}")
        summary_df["Predicted Visitors"] = summary_df["Predicted Visitors"].apply(lambda x: f"{x:,.0f}")

        st.table(summary_df)  # displays a clean, readable table

        # Optional: show slope, intercept, r² separately
        st.write(f"Slope: {results['slope']:.2f}")
        st.write(f"Intercept: {results['intercept']:.2f}")
        st.write(f"R²: {results['r2']:.2f}")

    except Exception as e:
        st.error(f"Error: {e}")
