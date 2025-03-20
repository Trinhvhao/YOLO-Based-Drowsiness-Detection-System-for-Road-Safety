import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

# Danh sách nhãn
labels = ['awake', 'drowsy', 'texting_phone', 'turning', 'talking_phone', 'background']
n_classes = len(labels)
total_images = 2000

# Tạo ma trận nhầm lẫn với độ chính xác cao
np.random.seed(42)
conf_matrix = np.zeros((n_classes, n_classes), dtype=int)

def generate_confusion_matrix():
    for i in range(n_classes):
        correct_predictions = int(0.95 * (total_images / n_classes))  # 90% đúng
        incorrect_predictions = (total_images // n_classes) - correct_predictions
        conf_matrix[i, i] = correct_predictions
        wrong_indices = [j for j in range(n_classes) if j != i]
        wrong_values = np.random.multinomial(incorrect_predictions, [1/(n_classes-1)]*(n_classes-1))
        for idx, val in zip(wrong_indices, wrong_values):
            conf_matrix[i, idx] = val
    return conf_matrix

conf_matrix = generate_confusion_matrix()

# Vẽ heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
plt.xlabel('True')
plt.ylabel('Predicted')
plt.title('Confusion Matrix')
plt.show()

# Xuất ma trận ra DataFrame để kiểm tra
conf_df = pd.DataFrame(conf_matrix, index=labels, columns=labels)
print(conf_df)