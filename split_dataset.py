import requests

# Cấu hình
API_KEY = "2217d2f15cf9c08795e0a0d5037de51d"  # Thay bằng API Key của bạn
CITY = "Hanoi"  # Thay bằng thành phố bạn muốn kiểm tra
URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric&lang=vi"


def get_weather():
    try:
        response = requests.get(URL)
        data = response.json()

        if response.status_code == 200:
            temp = data["main"]["temp"]
            weather = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            print(f"Thời tiết tại {CITY}: {weather.capitalize()}")
            print(f"Nhiệt độ: {temp}°C")
            print(f"Độ ẩm: {humidity}%")
            print(f"Tốc độ gió: {wind_speed} m/s")
        else:
            print("Lỗi lấy dữ liệu:", data["message"])

    except Exception as e:
        print("Lỗi:", e)


# Chạy kiểm tra
get_weather()
