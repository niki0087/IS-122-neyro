# video_processor.py
import os
import cv2
import tempfile
import torch
import numpy as np
from datetime import datetime, timedelta
from .model_utils import load_siz_model, get_violation_type, detect_gear_presence, parse_video_filename
from .database import add_report, get_workshop_by_camera

def process_videos(yolo_model_path, siz_model_path, video_dir, conn):
    """Обработка видеофайлов и сохранение нарушений с использованием YOLO для детекции людей"""
    yolo_model = torch.hub.load('ultralytics/yolov5', 'custom', path=yolo_model_path)
    siz_model = load_siz_model(siz_model_path)
    
    # Установка параметров для YOLO
    yolo_model.conf = 0.5
    yolo_model.classes = [0]
    
    for filename in os.listdir(video_dir):
        if not filename.lower().endswith(('.mp4', '.avi', '.mov')):
            continue
            
        camera_id, video_start_time = parse_video_filename(filename)
        if camera_id is None:
            print(f"Неверный формат имени файла: {filename}")
            continue
            
        video_path = os.path.join(video_dir, filename)
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Не удалось открыть видео: {filename}")
            continue
            
        # Получаем FPS видео
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        
        saved_violations = 0
        last_check_time = -10
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Вычисляем текущее время в видео (секунды)
            current_time = frame_count / fps
            
            if frame_count % 5 != 0:
                frame_count += 1
                continue
                
            # Детекция людей с помощью YOLO
            results = yolo_model(frame)
            people_detected = len(results.xyxy[0]) > 0
            
            if people_detected and (current_time - last_check_time >= 10):
                gear_ok = detect_gear_presence(siz_model, frame)
                
                if not gear_ok:
                    violation = get_violation_type(siz_model, frame)
                    
                    if violation:
                        # Создаем временное изображение
                        _, temp_img = tempfile.mkstemp(suffix=f'_{saved_violations}.jpg')
                        cv2.imwrite(temp_img, frame)
                        
                        workshop_number = get_workshop_by_camera(conn, camera_id)
                        if workshop_number is None:
                            os.remove(temp_img)
                            print(f"Не найден цех для камеры {camera_id}")
                        else:
                            # Рассчитываем время кадра
                            frame_time = video_start_time + timedelta(seconds=current_time)
                            
                            add_report(
                                conn=conn,
                                camera_id=camera_id,
                                violation_time=frame_time,
                                violation_type=violation,
                                photo_path=temp_img
                            )
                            
                            saved_violations += 1
                            print(f"Нарушение {saved_violations} в {filename} на {frame_time}: {violation}")
                
                last_check_time = current_time
            
            frame_count += 1
                
        cap.release()
        print(f"Обработка завершена: {filename}. Найдено нарушений: {saved_violations}")