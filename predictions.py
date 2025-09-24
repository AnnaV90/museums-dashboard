import requests

url = "http://127.0.0.1:8000/predict"
params = {"pops": "2000000,5000000,10000000"}

response = requests.get(url, params=params)
print(response.json())
