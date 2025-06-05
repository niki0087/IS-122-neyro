# model_utils.py
import torch
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
import re

VIOLATION_TYPES = {
    "no_helmet": "Отсутствует каска",
    "no_uniform": "Отсутствует спецовка",
    "both": "Отсутствует каска и спецовка"
}

def load_siz_model(model_path):
    """Загрузка модели для детекции СИЗ"""
    model = torch.jit.load(model_path, map_location='cpu')
    model.eval()
    return model

def detect_gear_presence(model, image):
    """
    Проверяет наличие СИЗ на изображении.
    Возвращает True, если все СИЗ присутствуют, иначе False.
    """
    # Конвертируем BGR (OpenCV) в RGB
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    img = img.resize((128, 128))
    
    # Преобразование в numpy array и нормализация
    img_array = np.array(img).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array - mean) / std
    
    # Преобразование в тензор
    img_tensor = torch.tensor(img_array, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)
    
    with torch.no_grad():
        outputs = model(img_tensor)
    
    # Вероятность присутствия СИЗ
    helmet_present = outputs[0, 0].item() > 0.5
    uniform_present = outputs[0, 1].item() > 0.5
    
    return helmet_present and uniform_present

def get_violation_type(model, image):
    """
    Определяет тип нарушения на изображении.
    Возвращает строку с описанием нарушения или None, если нарушений нет.
    """
    # Конвертируем BGR (OpenCV) в RGB
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    img = img.resize((128, 128))
    
    # Преобразование в numpy array и нормализация
    img_array = np.array(img).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array - mean) / std
    
    # Преобразование в тензор
    img_tensor = torch.tensor(img_array, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)
    
    with torch.no_grad():
        outputs = model(img_tensor)
    
    # Вероятность присутствия СИЗ
    helmet_present = outputs[0, 0].item() > 0.5
    uniform_present = outputs[0, 1].item() > 0.5
    
    if helmet_present and uniform_present:
        return None
    
    violations = []
    if not helmet_present:
        violations.append(VIOLATION_TYPES["no_helmet"])
    if not uniform_present:
        violations.append(VIOLATION_TYPES["no_uniform"])
    
    return ", ".join(violations)

def parse_video_filename(filename):
    """Парсинг информации из имени видеофайла"""
    # Паттерн для формата CAMERA1_08:07:19.06.04.2025.mp4
    pattern = r'CAMERA(\d+)_(\d{2}:\d{2}:\d{2})\.(\d{2}\.\d{2}\.\d{4})'
    match = re.match(pattern, filename)
    
    if match:
        camera_id = int(match.group(1))
        time_str = match.group(2)
        date_str = match.group(3)
        
        # Форматируем дату из DD.MM.YYYY в YYYY-MM-DD
        day, month, year = date_str.split('.')
        formatted_date = f"{year}-{month}-{day}"
        
        try:
            violation_time = datetime.strptime(f"{formatted_date} {time_str}", "%Y-%m-%d %H:%M:%S")
            return camera_id, violation_time
        except ValueError as e:
            print(f"Ошибка преобразования времени: {formatted_date} {time_str} - {str(e)}")
            return None, None
    
    print(f"Неверный формат имени файла: {filename}")
    return None, None