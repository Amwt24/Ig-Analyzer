import httpx
import json

api_key = "0fe856b482msh0cb0dd37695b479p139098jsnb2404fb83b9a"
host = "instagram-scraper-stable-api.p.rapidapi.com"

def get_user_info():
    url = f"https://{host}/get_ig_user_followers_v2.php"
    headers = {
        "x-rapidapi-host": host,
        "x-rapidapi-key": api_key,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "username_or_url": "https://www.instagram.com/adorn_quran/",
        "data": "following",
        "amount": "12",
        "pagination_token": ""
    }
    resp = httpx.post(url, headers=headers, data=data)
    print("info:", resp.status_code, resp.text)

if __name__ == "__main__":
    get_user_info()
