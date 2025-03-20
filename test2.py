import cv2
from ultralytics import YOLO
from gtts import gTTS
import os
import time
import random
import threading
import requests
import tkinter as tk
from tkinter import ttk
import logging

# Tắt logging của ultralytics
logging.getLogger("ultralytics").setLevel(logging.WARNING)

# Load model YOLO
model = YOLO("runs/detect/train17/weights/best.pt")

# Ánh xạ class ID sang tên nhãn
class_names = {
    0: 'awake',
    1: 'drowsy',
    2: 'texting_phone',
    3: 'turning',
    4: 'talking_phone'
}

# Cấu hình cảnh báo
alert_cooldowns = {
    'drowsy': 15,
    'texting_phone': 10,
    'talking_phone': 8,
    'turning': 5
}

# Thời gian yêu cầu hành vi kéo dài để phát cảnh báo
DETECTION_DURATION_THRESHOLD = 3

# Từ điển lưu thời gian và số lần phát hiện
detection_start_times = {class_name: None for class_name in alert_cooldowns.keys()}
last_alert_times = {class_name: 0 for class_name in alert_cooldowns.keys()}
detection_counts = {class_name: 0 for class_name in alert_cooldowns.keys()}

# Danh sách câu thoại cảnh báo
alert_messages = {
    'drowsy': [
        "Bạn có mệt không? Cần dừng lại nghỉ ngơi không?",
        "Tình trạng buồn ngủ phát hiện! Bạn cần tập trung!",
        "Hệ thống phát hiện mệt mỏi, đề nghị nghỉ ngơi!",
        "Buồn ngủ rồi à? Hay mình tìm chỗ nghỉ một chút nhé!",
        "Mắt bạn có vẻ nặng rồi, nghỉ chút cho tỉnh táo nào!",
        "Bạn có muốn dừng lại uống cà phê không? Nói 'có' nếu muốn nhé!"
    ],
    'texting_phone': [
        "Bạn ơi, nguy hiểm lắm! Đừng nhắn tin khi lái xe!",
        "Việc nhắn tin có thể đợi, tập trung lái xe bạn nhé!",
        "Nguy hiểm! Xin đừng sử dụng điện thoại!",
        "Điện thoại quan trọng, nhưng an toàn còn hơn, bạn nhé!",
        "Nhắn tin bây giờ là đánh cược mạng sống đấy bạn ơi!",
        "Tin nhắn không chạy mất đâu, để yên cho mình lái xe nào!"
    ],
    'talking_phone': [
        "Bạn vui lòng dùng tai nghe để đàm thoại an toàn!",
        "Trò chuyện điện thoại làm giảm tập trung lái xe!",
        "Xin hãy dừng xe nếu cần gọi điện khẩn cấp!",
        "Nói chuyện sau cũng được mà, giờ tập trung lái xe nhé bạn!",
        "Dùng tai nghe đi bạn, vừa an toàn vừa tiện!",
        "Cuộc gọi quan trọng thì dừng xe đã, đừng mạo hiểm!"
    ],
    'turning': [
        "Chú ý quan sát trước khi chuyển hướng!",
        "Xin bật xi-nhan trước khi rẽ!",
        "Giảm tốc độ khi vào cua bạn nhé!",
        "Quan sát gương chiếu hậu trước khi rẽ, bạn nhớ nhé!",
        "Cẩn thận xe phía sau khi chuyển hướng nha bạn!",
        "Xi-nhan bật chưa bạn? Rẽ từ từ thôi!"
    ]
}

# Cấu hình Telegram Bot
TELEGRAM_BOT_TOKEN = "7609118704:AAG_YkdgqxUs9jV6UP1LpgQ_lp7_2DCx0hs"  # Thay bằng token của bot Telegram
TELEGRAM_CHAT_ID = "6597950453"    # Thay bằng chat ID của bạn hoặc nhóm

# Hàm gửi video qua Telegram
def send_video_to_telegram(file_path, class_name):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        with open(file_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': f"Phát hiện hành vi: {class_name} lúc {time.strftime('%H:%M:%S %d/%m/%Y')}"
            }
            response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            print(f"Đã gửi video {file_path} đến Telegram.")
        else:
            print(f"Lỗi gửi video đến Telegram: {response.text}")
        os.remove(file_path)  # Xóa file sau khi gửi
    except Exception as e:
        print(f"Lỗi khi gửi video qua Telegram: {e}")

# Hàm phát giọng nói
def speak_alert(message):
    try:
        print("ALERT:", message)
        tts = gTTS(text=message, lang="vi", slow=False)
        tts.save("alert.mp3")
        from playsound import playsound
        playsound("alert.mp3")
        os.remove("alert.mp3")
    except Exception as e:
        print(f"Lỗi khi phát âm thanh: {e}")

# Hàm ghi video khi phát hiện hành vi nguy hiểm
def record_video(frame, class_name):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_path = f"record_{class_name}_{timestamp}.avi"
    out = cv2.VideoWriter(file_path, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
    start_time = time.time()
    while time.time() - start_time < 15:  # Ghi 15 giây
        ret, rec_frame = cap.read()
        if ret:
            out.write(rec_frame)
        time.sleep(0.05)
    out.release()
    print(f"Đã ghi video: {file_path}")
    # Gửi video qua Telegram nếu là hành vi 'drowsy'
    if class_name == 'drowsy':
        threading.Thread(target=send_video_to_telegram, args=(file_path, class_name), daemon=True).start()

# Hàm lấy thời gian trong ngày
def get_time_context():
    hour = time.localtime().tm_hour
    if 5 <= hour < 12:
        return "sáng"
    elif 12 <= hour < 17:
        return "chiều"
    elif 17 <= hour < 22:
        return "tối"
    else:
        return "đêm"

# Hàm lấy dữ liệu thời tiết từ OpenWeatherMap
def get_weather_data(lat=21.0278, lon=105.8342):  # Mặc định là Hà Nội
    api_key = "2217d2f15cf9c08795e0a0d5037de51d"
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        weather = data['weather'][0]['main'].lower()
        temp = data['main']['temp']
        city = data['name']
        return weather, temp, city
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu thời tiết: {e}")
        return "unknown", 25, "Unknown"

# Hàm tạo cảnh báo dựa trên thời tiết
def get_weather_alert(class_name, weather, temp, time_context):
    weather_messages = {
        'rain': "Trời đang mưa, bạn cẩn thận đường trơn nhé!",
        'fog': "Sương mù dày đặc, bạn giảm tốc độ và bật đèn đi nhé!",
        'clear': "Trời quang đãng, nhưng bạn vẫn cần tập trung!",
        'clouds': "Trời nhiều mây, chú ý tầm nhìn hạn chế nha bạn!"
    }
    temp_messages = {
        'hot': "Trời nóng quá, bạn nhớ uống nước để tỉnh táo nhé!",
        'cold': "Trời lạnh rồi, bạn giữ ấm để lái xe an toàn!"
    }

    base_message = random.choice(alert_messages[class_name])
    weather_message = weather_messages.get(weather, "")
    temp_message = temp_messages['hot'] if temp > 30 else temp_messages['cold'] if temp < 15 else ""

    if random.random() < 0.5:
        if weather_message and temp_message:
            return f"Buổi {time_context} {weather_message} {temp_message} {base_message}"
        elif weather_message:
            return f"Buổi {time_context} {weather_message} {base_message}"
        else:
            return f"Buổi {time_context} mà {base_message}"
    return base_message

# Thời gian bắt đầu lái xe
start_time = time.time()

# Khởi tạo GUI bằng tkinter
root = tk.Tk()
root.title("Driver Monitoring System")
root.geometry("400x300")
root.resizable(False, False)

# Các nhãn hiển thị trạng thái
status_label = ttk.Label(root, text="Trạng thái: Đang chạy", font=("Arial", 12))
status_label.pack(pady=10)

behavior_label = ttk.Label(root, text="Hành vi: Chưa phát hiện", font=("Arial", 10))
behavior_label.pack(pady=5)

weather_label = ttk.Label(root, text="Thời tiết: Đang cập nhật", font=("Arial", 10))
weather_label.pack(pady=5)

location_label = ttk.Label(root, text="Địa điểm: Đang cập nhật", font=("Arial", 10))
location_label.pack(pady=5)

time_label = ttk.Label(root, text="Thời gian: Đang cập nhật", font=("Arial", 10))
time_label.pack(pady=5)

driving_time_label = ttk.Label(root, text="Thời gian lái: 0 phút", font=("Arial", 10))
driving_time_label.pack(pady=5)


# Hàm cập nhật GUI với màu sắc
def update_gui(behavior, weather, temp, city, current_time_str, driving_time):
    behavior_label.config(text=f"Hành vi: {behavior}")
    if behavior == "awake":
        behavior_label.config(foreground="green")  # Xanh lá cho trạng thái tỉnh táo
    elif behavior in alert_cooldowns:  # Các hành vi nguy hiểm
        behavior_label.config(foreground="red")  # Đỏ cho hành vi nguy hiểm
    else:
        behavior_label.config(foreground="black")  # Đen cho "Chưa phát hiện"

    weather_label.config(text=f"Thời tiết: {weather}, {temp}°C")
    location_label.config(text=f"Địa điểm: {city}")
    time_label.config(text=f"Thời gian: {current_time_str}")
    driving_time_label.config(text=f"Thời gian lái: {driving_time:.0f} phút")
    root.update()

# Mở webcam
cap = cv2.VideoCapture(0)

# Biến lưu thời gian cập nhật thời tiết
last_weather_update = 0
weather_update_interval = 300  # Cập nhật mỗi 5 phút
current_weather, current_temp, current_city = "unknown", 25, "Unknown"

# Chạy GUI trong thread riêng
def run_gui():
    root.mainloop()

gui_thread = threading.Thread(target=run_gui, daemon=True)
gui_thread.start()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Không thể lấy dữ liệu từ webcam!")
        break

    # Dự đoán bằng YOLO với verbose=False để tắt thông báo
    results = model(frame, conf=0.65, verbose=False)
    annotated_frame = results[0].plot()

    current_time = time.time()
    detected_classes = set()

    # Tính thời gian lái xe (phút)
    driving_time = (current_time - start_time) / 60

    # Cập nhật thời tiết
    if current_time - last_weather_update > weather_update_interval:
        current_weather, current_temp, current_city = get_weather_data(lat=21.0278, lon=105.8342)
        last_weather_update = current_time
        print(f"Địa điểm: {current_city}, Thời tiết: {current_weather}, Nhiệt độ: {current_temp}°C")

    # Lấy thông tin class phát hiện được
    for box in results[0].boxes:
        class_id = int(box.cls)
        class_name = class_names.get(class_id, 'unknown')
        detected_classes.add(class_name)

    # Xử lý hành vi và phát cảnh báo
    time_context = get_time_context()
    detected_behavior = "Chưa phát hiện"  # Giá trị mặc định

    if detected_classes:  # Nếu có hành vi được phát hiện
        detected_behavior = list(detected_classes)[0]

    # Xử lý cảnh báo và ghi video cho các hành vi nguy hiểm
    for class_name in alert_cooldowns:
        if class_name in detected_classes:
            if detection_start_times[class_name] is None:
                detection_start_times[class_name] = current_time
            else:
                elapsed_time = current_time - detection_start_times[class_name]
                if elapsed_time >= DETECTION_DURATION_THRESHOLD:
                    cooldown = alert_cooldowns[class_name]
                    last_time = last_alert_times[class_name]

                    if current_time - last_time > cooldown:
                        detection_counts[class_name] += 1
                        message = get_weather_alert(class_name, current_weather, current_temp, time_context)
                        if detection_counts[class_name] > 3:
                            message = f"Bạn ơi, lần này là lần thứ {detection_counts[class_name]} rồi! {message}"
                        threading.Thread(target=speak_alert, args=(message,), daemon=True).start()
                        threading.Thread(target=record_video, args=(frame, class_name), daemon=True).start()
                        last_alert_times[class_name] = current_time
                        detection_start_times[class_name] = None
        else:
            detection_start_times[class_name] = None

    # Hiển thị thông tin trên khung hình OpenCV
    current_time_str = time.strftime("%H:%M:%S %d/%m/%Y")
    weather_info = f"Thoi tiet: {current_weather}, {current_temp}°C"
    location_info = f"Dia diem: {current_city}"

    cv2.putText(annotated_frame, current_time_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(annotated_frame, location_info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(annotated_frame, weather_info, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Cập nhật GUI
    update_gui(detected_behavior, current_weather, current_temp, current_city, current_time_str, driving_time)

    # Hiển thị frame OpenCV
    cv2.imshow("Driver Monitoring", annotated_frame)

    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()
root.quit()