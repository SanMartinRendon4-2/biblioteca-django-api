import requests

URL = "http://127.0.0.1:8000/o/token/"
CLIENT_ID = "etzJKGworBqUtZZR6HaNAFQ02jdXViQdUVU0tsgk"
CLIENT_SECRET = "CXi0qj8P0D7DhKFEtXx5cFnuc6aIJdRkRTqdCmEQpQP6EdFw2Aekz5eaj4M4TktdSHKvaJKk79aUs6l38td2N5YFNcy4GXDcWZ7FU5BpCTETVCgGiXLP5Eyp6pBEatRD"

data = {
    "grant_type": "password",
    "username": "admin",
    "password": "admin123",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

try:
    response = requests.post(URL, data=data)
    print(f"Estado: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")