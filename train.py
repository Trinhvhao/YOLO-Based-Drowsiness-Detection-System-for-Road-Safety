from ultralytics import YOLO
import albumentations as A

def main():
    # --------------------------------------------------
    # Data Augmentation (Áp dụng tự động khi train)
    # --------------------------------------------------
    augmentation = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(p=0.2),
        A.Blur(blur_limit=3, p=0.1),
        A.MotionBlur(blur_limit=3, p=0.1),
        A.Rotate(limit=10, p=0.3),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))

    # --------------------------------------------------
    # Load Pretrained Model và Train
    # --------------------------------------------------
    model = YOLO('yolov8s.pt')  # Load model pretrained trên COCO

    # Train với hyperparameters tùy chỉnh
    results = model.train(
        data='dataset.yaml',
        epochs=50,
        imgsz=640,
        batch=16,
        augment=True,  # Tự động áp dụng augmentation
        lr0=0.001,
        optimizer='Adam',
        mixup=0.2,      # Tăng cường mixup để giảm overfit
        dropout=0.2,    # Thêm dropout
        weight_decay=0.0005,
        degrees=10,     # Xoay ảnh
        flipud=0.1,     # Lật dọc
        fliplr=0.5,     # Lật ngang
    )

if __name__ == "__main__":
    # Thêm freeze_support() nếu đóng băng thành file .exe
    # từ pyinstaller hoặc tương tự
    main()