import cv2
import numpy as np
import time
import threading
from bluetooth import *
import torch

# Cấu hình hệ thống
CONFIDENCE_THRESHOLD = 0.7
ALERT_DURATIONS = {
    'drowsy': 3.0,
    'texting_phone': 5.0,
    'talking_phone': 5.0,
    'turning': 4.0
}
BLUETOOTH_DEVICE_NAME = "YOUR_BT_SPEAKER_NAME"
FRAME_SIZE = (640, 480)


class BluetoothManager:
    def __init__(self):
        self.socket = None
        self.connected = False

    def connect(self):
        try:
            devices = discover_devices(duration=5, lookup_names=True)
            for addr, name in devices:
                if name == BLUETOOTH_DEVICE_NAME:
                    self.socket = BluetoothSocket(RFCOMM)
                    self.socket.connect((addr, 1))
                    self.connected = True
                    print("✅ Bluetooth connected")
                    return True
            return False
        except Exception as e:
            print(f"Bluetooth connection error: {str(e)}")
            return False

    def send_alert(self, message):
        if self.connected:
            try:
                self.socket.send(f"ALERT:{message}\n")
            except Exception as e:
                print(f"Send error: {str(e)}")
                self.connected = False


class DrowsinessMonitor:
    def __init__(self, model_path):
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
        self.state_history = {}
        self.bt_manager = BluetoothManager()
        self.bt_connect_thread = threading.Thread(target=self.bt_manager.connect)
        self.bt_connect_thread.start()

        # Class mapping theo dataset
        self.class_map = {
            0: 'awake',
            1: 'drowsy',
            2: 'texting_phone',
            3: 'turning',
            4: 'talking_phone'
        }

    def process_frame(self, frame):
        results = self.model(frame, size=FRAME_SIZE[0])
        return results.pandas().xyxy[0]

    def update_state(self, detections):
        current_states = {}
        for _, det in detections.iterrows():
            if det['confidence'] > CONFIDENCE_THRESHOLD:
                class_name = self.class_map.get(det['class'], 'unknown')
                current_states[class_name] = time.time()

        # Cập nhật state history
        for state in ALERT_DURATIONS:
            if state in current_states:
                if state not in self.state_history:
                    self.state_history[state] = {'start_time': time.time(), 'alerted': False}
                else:
                    duration = time.time() - self.state_history[state]['start_time']
                    if duration >= ALERT_DURATIONS[state] and not self.state_history[state]['alerted']:
                        self.trigger_alert(state)
                        self.state_history[state]['alerted'] = True
            else:
                if state in self.state_history:
                    del self.state_history[state]

    def trigger_alert(self, state):
        alert_messages = {
            'drowsy': "Driver is drowsy! Please take a break!",
            'texting_phone': "Warning: Phone usage detected while driving!",
            'talking_phone': "Hands-free device required!",
            'turning': "Keep both hands on the wheel!"
        }

        message = alert_messages.get(state, "Unsafe driving detected!")
        print(f"ALERT: {message}")
        threading.Thread(target=self.bt_manager.send_alert, args=(message,)).start()

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(3, FRAME_SIZE[0])
        cap.set(4, FRAME_SIZE[1])

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Xử lý frame
                detections = self.process_frame(frame)
                self.update_state(detections)

                # Hiển thị thông tin
                cv2.putText(frame, f"Current State: {self.get_current_state()}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('Driver Monitoring System', frame)

                if cv2.waitKey(1) == 27:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            if self.bt_manager.connected:
                self.bt_manager.socket.close()

    def get_current_state(self):
        for state in self.state_history:
            if not self.state_history[state]['alerted']:
                return state
        return 'normal'


if __name__ == "__main__":
    monitor = DrowsinessMonitor("best.pt")  # Thay bằng model path của bạn
    monitor.run()