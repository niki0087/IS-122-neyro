import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                             QFileDialog, QLineEdit, QLabel, QMessageBox, QDialog, 
                             QListWidget, QComboBox, QInputDialog, QHBoxLayout, QListWidgetItem)
from PyQt5.QtCore import Qt
from .database import create_database, connect_database, add_workshop, add_camera, get_all_workshops, get_all_reports, get_report_photo
from .report_generator import generate_report_pdf

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Подключение к БД")
        self.setFixedSize(400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.db_path_edit = QLineEdit()
        self.user_edit = QLineEdit("SYSDBA")
        self.password_edit = QLineEdit("masterkey")
        self.password_edit.setEchoMode(QLineEdit.Password)
        
        layout.addWidget(QLabel("Путь к БД (.fdb):"))
        layout.addWidget(self.db_path_edit)
        layout.addWidget(QLabel("Пользователь:"))
        layout.addWidget(self.user_edit)
        layout.addWidget(QLabel("Пароль:"))
        layout.addWidget(self.password_edit)
        
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Создать БД")
        connect_btn = QPushButton("Подключиться к БД")
        create_btn.clicked.connect(self.create_db)
        connect_btn.clicked.connect(self.connect_db)
        
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(connect_btn)
        layout.addLayout(btn_layout)
        
        # Кнопка выбора файла БД
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self.browse_db_path)
        layout.addWidget(browse_btn)
        
    def browse_db_path(self):
        path, _ = QFileDialog.getSaveFileName(self, "Создать файл БД", "", "Firebird Database (*.fdb)")
        if path:
            if not path.endswith('.fdb'):
                path += '.fdb'
            self.db_path_edit.setText(path)
            
    def create_db(self):
        path = self.db_path_edit.text()
        user = self.user_edit.text()
        password = self.password_edit.text()
        
        if not path:
            QMessageBox.critical(self, "Ошибка", "Укажите путь для создания БД")
            return
            
        # Проверяем формат пути (не должен содержать :)
        if ':' in path:
            QMessageBox.critical(self, "Ошибка", 
                "Для создания базы данных используйте локальный путь\n"
                "Пример: /home/nikita/neyro.fdb")
            return
            
        try:
            # Создаем БД
            success = create_database(path, user, password)
            if success:
                # Если создание успешно, подключаемся
                self.conn = connect_database(path, user, password)
                self.open_main_window()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать БД")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать БД: {str(e)}")
            
    def connect_db(self):
        path = self.db_path_edit.text()
        user = self.user_edit.text()
        password = self.password_edit.text()
        
        try:
            self.conn = connect_database(path, user, password)
            self.open_main_window()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения: {str(e)}")
            
    def open_main_window(self):
        self.main_window = MainWindow(self.conn)
        self.main_window.show()
        self.hide()

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.setWindowTitle("Детекция нарушений СИЗ")
        self.setFixedSize(400, 450)
        self.conn = conn
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        buttons = [
            ("Посмотреть отчет", self.view_reports),
            ("Подключиться к камерам", self.connect_cameras),
            ("Выбрать модель СИЗ", self.select_model),
            ("Выбрать модель YOLO", self.select_yolo_model),
            ("Добавить камеру", self.add_camera),
            ("Добавить цех", self.add_workshop),
            ("Начать работу", self.start_processing)
        ]
        
        for text, handler in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
            
        self.video_dir = None
        self.model_path = None
        self.yolo_model_path = None
        
    def view_reports(self):
        try:
            reports = get_all_reports(self.conn)
            if not reports:
                QMessageBox.information(self, "Отчеты", "Нет доступных отчетов")
                return
                
            self.reports_window = ReportsWindow(reports, self.conn)
            self.reports_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка получения отчетов: {str(e)}")
        
    def connect_cameras(self):
        self.video_dir = QFileDialog.getExistingDirectory(self, "Выберите директорию с видео")
        if self.video_dir:
            QMessageBox.information(self, "Успех", f"Директория выбрана: {self.video_dir}")
        
    def select_model(self):
        self.model_path, _ = QFileDialog.getOpenFileName(self, "Выберите модель СИЗ", "", "Model Files (*.pt)")
        if self.model_path:
            QMessageBox.information(self, "Успех", f"Модель СИЗ выбрана: {os.path.basename(self.model_path)}")
            
    def select_yolo_model(self):
        self.yolo_model_path, _ = QFileDialog.getOpenFileName(self, "Выберите модель YOLO", "", "Model Files (*.pt)")
        if self.yolo_model_path:
            QMessageBox.information(self, "Успех", f"Модель YOLO выбрана: {os.path.basename(self.yolo_model_path)}")
        
    def add_workshop(self):
        number, ok = QInputDialog.getInt(self, "Добавить цех", "Номер цеха:")
        if ok:
            try:
                add_workshop(self.conn, number)
                QMessageBox.information(self, "Успех", "Цех добавлен")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка добавления: {str(e)}")
                
    def add_camera(self):
        try:
            workshops = get_all_workshops(self.conn)
            if not workshops:
                QMessageBox.critical(self, "Ошибка", "Сначала добавьте цех")
                return
                
            dialog = QDialog(self)
            dialog.setWindowTitle("Добавить камеру")
            dialog.setFixedSize(300, 200)
            layout = QVBoxLayout(dialog)
            
            layout.addWidget(QLabel("Номер камеры:"))
            camera_edit = QLineEdit()
            layout.addWidget(camera_edit)
            
            layout.addWidget(QLabel("Цех:"))
            workshop_combo = QComboBox()
            workshop_combo.addItems([f"Цех {w[1]}" for w in workshops])
            layout.addWidget(workshop_combo)
            
            btn_layout = QHBoxLayout()
            cancel_btn = QPushButton("Отмена")
            add_btn = QPushButton("Добавить")
            
            cancel_btn.clicked.connect(dialog.reject)
            add_btn.clicked.connect(lambda: self.save_camera(
                dialog, camera_edit.text(), workshop_combo.currentText()
            ))
            
            btn_layout.addWidget(cancel_btn)
            btn_layout.addWidget(add_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")
        
    def save_camera(self, dialog, camera_id, workshop_text):
        try:
            camera_id = int(camera_id)
            workshop_number = int(workshop_text.split()[-1])
            
            # Найти ID цеха по номеру
            workshops = get_all_workshops(self.conn)
            workshop_id = next(w[0] for w in workshops if w[1] == workshop_number)
            
            add_camera(self.conn, camera_id, workshop_id)
            QMessageBox.information(self, "Успех", "Камера добавлена")
            dialog.close()
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Номер камеры должен быть целым числом")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка добавления: {str(e)}")
        
    def start_processing(self):
        # Отложенный импорт, чтобы избежать ранней загрузки OpenCV
        from .video_processor import process_videos
        
        if not self.model_path:
            QMessageBox.critical(self, "Ошибка", "Сначала выберите модель СИЗ")
            return
        if not self.yolo_model_path:
            QMessageBox.critical(self, "Ошибка", "Сначала выберите модель YOLO")
            return
        if not self.video_dir:
            QMessageBox.critical(self, "Ошибка", "Сначала выберите директорию с видео")
            return
            
        try:
            process_videos(self.yolo_model_path, self.model_path, self.video_dir, self.conn)
            QMessageBox.information(self, "Успех", "Обработка видео завершена")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка обработки: {str(e)}")

class ReportsWindow(QDialog):
    def __init__(self, reports, conn):
        super().__init__()
        self.setWindowTitle("Отчеты")
        self.setFixedSize(600, 400)
        self.conn = conn
        self.reports = reports  # Сохраняем оригинальные данные отчетов
        
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        
        for report in reports:
            item_text = (f"Цех {report[4]}, Камера {report[1]}, "
                         f"{report[2].strftime('%Y-%m-%d %H:%M:%S')}, "
                         f"{report[3]}")
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, report[0])  # Сохраняем ID отчета
            self.list_widget.addItem(item)
            
        self.list_widget.itemDoubleClicked.connect(self.generate_report)
        layout.addWidget(self.list_widget)
        
    def generate_report(self, item):
        report_id = item.data(Qt.UserRole)
        try:
            # Находим полные данные отчета по ID
            report = next((r for r in self.reports if r[0] == report_id), None)
            if not report:
                QMessageBox.critical(self, "Ошибка", "Данные отчета не найдены")
                return
                
            photo_data = get_report_photo(self.conn, report_id)
            
            if not photo_data:
                QMessageBox.critical(self, "Ошибка", "Фото отчета не найдено")
                return
                
            # Сохраняем временное изображение
            temp_img_path = f"temp_report_{report_id}.jpg"
            with open(temp_img_path, 'wb') as f:
                f.write(photo_data)
                
            # Генерируем PDF
            pdf_path = f"report_{report_id}.pdf"
            
            # Используем оригинальные данные отчета
            workshop_number = report[4]  # WORKSHOP_NUMBER
            camera_id = report[1]        # CAMERA_ID
            violation_time = report[2].strftime('%Y-%m-%d %H:%M:%S')  # VIOLATION_TIME
            violation_type = report[3]    # VIOLATION_TYPE
            
            generate_report_pdf(
                image_path=temp_img_path,
                workshop_number=workshop_number,
                camera_id=camera_id,
                violation_time=violation_time,
                violation_type=violation_type,
                output_path=pdf_path
            )
            
            # Открываем PDF
            if sys.platform == 'win32':  # Windows
                os.startfile(pdf_path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{pdf_path}"')
            else:  # Linux и другие UNIX-системы
                os.system(f'xdg-open "{pdf_path}"')
                
            # Удаляем временное изображение после использования
            os.remove(temp_img_path)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка генерации отчета: {str(e)}")

def start_app():
    # Для Linux: устанавливаем платформу xcb
    if sys.platform.startswith('linux'):
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())