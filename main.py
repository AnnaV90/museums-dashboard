from fastapi import FastAPI, Query
import pandas as pd
import numpy as np
from fuzzywuzzy import process
from sklearn.linear_model import LinearRegression
import time
import pycountry
import wikipedia
from io import StringIO
import requests

# Load city populations CSV once at startup
CSV_PATH = "/Users/annavaugrante/PycharmProjects/museums/worldcities.csv"
CITIES_DF = pd.read_csv(CSV_PATH)

app = FastAPI(title="Museums API")


class Preprocessing:
    def clean_number(self, val):
        if isinstance(val, str):
            v = val[:9].replace(",", "").lower().strip()
            if v.endswith(("mil", "milli", "mill")):
                num = "".join(c for c in v if c.isdigit() or c == ".")
                return float(num) * 1_000_000
            try:
                return float(v)
            except ValueError:
                return None
        return val

    def clean_city_name(self, city):
        return city.split(",")[0].strip()

    def country_to_iso2(self, name):
        if not name or pd.isna(name):
            return None
        try:
            return pycountry.countries.lookup(name).alpha_2
        except LookupError:
            # Fallback custom map
            custom_map = {
                "Turkey": "TR",
                "Vatican": "VA",
                "Russia": "RU",
                "Iran": "IR",
                "South Korea": "KR",
                "North Korea": "KP",
            }
            return custom_map.get(name.strip(), None)

    def get_population(self, city, country_code=None):
        df = CITIES_DF
        # Exact match first
        subset = df[df["city_ascii"].str.lower() == city.lower()]
        if country_code:
            subset = subset[subset["iso2"] == country_code]
        if not subset.empty:
            row = subset.loc[subset["population"].idxmax()]
            return int(row["population"]) if not pd.isna(row["population"]) else None

        # Fuzzy match fallback
        match, score = process.extractOne(city, df["city_ascii"].unique())
        if score > 85:
            row = df[df["city_ascii"] == match].iloc[0]
            return int(row["population"]) if not pd.isna(row["population"]) else None

        return None


class Prediction:
    def __init__(self, data):
        self.data = data.dropna(subset=["Visitors in 2024", "Population"]).copy()
        self.model = None

    def fit(self):
        X = self.data[["Population"]].values
        y = self.data["Visitors in 2024"].values
        self.model = LinearRegression()
        self.model.fit(X, y)
        return {
            "slope": self.model.coef_[0],
            "intercept": self.model.intercept_,
            "r2": self.model.score(X, y),
        }

    def predict(self, populations):
        if self.model is None:
            raise ValueError("Model not trained yet.")
        populations = np.array(populations).reshape(-1, 1)
        return self.model.predict(populations)


# --- New function 1: get dataframe ---
def get_museum_dataframe():
    prep = Preprocessing()
    url = "https://en.wikipedia.org/wiki/List_of_most-visited_museums#Most-visited_museums_in_2024"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    html = StringIO(response.text)
    data = pd.read_html(html)[0]

    data["Visitors in 2024"] = data["Visitors in 2024"].apply(prep.clean_number)
    data["City"] = data["City"].apply(prep.clean_city_name)
    data["Country Code"] = data["Country"].apply(prep.country_to_iso2)

    populations = [prep.get_population(row["City"], row.get("Country Code"))
                   for _, row in data.iterrows()]
    data["Population"] = populations
    data = data.dropna(subset=["Population", "Visitors in 2024"])
    data["ratio"] = data["Visitors in 2024"] / data["Population"]
    Q1 = data["ratio"].quantile(0.25)
    Q3 = data["ratio"].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    data = data[(data["ratio"] >= lower_bound) & (data["ratio"] <= upper_bound)]
    data = data.reset_index(drop=True)
    return data


# --- New function 2: make predictions ---
def make_predictions(data, pops):
    predictor = Prediction(data)
    results = predictor.fit()
    new_pops = [int(p.strip()) for p in pops.split(",")]
    predictions = predictor.predict(new_pops)
    return {
        "slope": results["slope"],
        "intercept": results["intercept"],
        "r2": results["r2"],
        "predictions": predictions.tolist(),
    }


@app.get("/")
def root():
    return {"message": "Hello from Museums API"}


@app.get("/predict")
def predict_visitors(pops: str = Query("1000000,5000000,10000000")):
    try:
        data = get_museum_dataframe()
        return make_predictions(data, pops)
    except Exception as e:
        return {"error": str(e)}
