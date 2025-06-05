import firebird.driver as fdb
import os
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database(path, user, password):
    """Создание новой базы данных с необходимыми таблицами"""
    try:
        # Преобразуем путь в абсолютный
        path = os.path.abspath(path)
        logger.info(f"Создание БД: {path}")
        
        # Создаем директорию, если ее нет
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Удаляем существующий файл, если есть
        if os.path.exists(path):
            logger.warning(f"Файл БД {path} уже существует, удаляем...")
            os.remove(path)
        
        # Создание БД - единый формат строки подключения
        connection_string = f"localhost/3050:{path}"
        con = fdb.create_database(
            connection_string,
            user=user,
            password=password
        )
        
        # Выполнение DDL
        cur = con.cursor()
        
        # Таблица Цеха
        cur.execute("""
            CREATE TABLE WORKSHOPS (
                WORKSHOP_ID INTEGER PRIMARY KEY,
                WORKSHOP_NUMBER INTEGER NOT NULL UNIQUE
            )
        """)
        
        # Таблица Камеры
        cur.execute("""
            CREATE TABLE CAMERAS (
                CAMERA_ID INTEGER PRIMARY KEY,
                WORKSHOP_ID INTEGER NOT NULL REFERENCES WORKSHOPS(WORKSHOP_ID)
            )
        """)
        
        # Таблица Отчеты
        cur.execute("""
            CREATE TABLE REPORTS (
                REPORT_ID INTEGER PRIMARY KEY,
                CAMERA_ID INTEGER NOT NULL REFERENCES CAMERAS(CAMERA_ID),
                VIOLATION_TIME TIMESTAMP NOT NULL,
                VIOLATION_TYPE VARCHAR(100) NOT NULL,  -- Увеличено до 100 символов
                PHOTO BLOB SUB_TYPE 0 SEGMENT SIZE 16384
            )
        """)
        
        # Генераторы для первичных ключей
        cur.execute("CREATE SEQUENCE GEN_WORKSHOP_ID")
        cur.execute("CREATE SEQUENCE GEN_CAMERA_ID")
        cur.execute("CREATE SEQUENCE GEN_REPORT_ID")
        
        # Триггеры для автоинкремента
        cur.execute("""
            CREATE TRIGGER WORKSHOPS_BI FOR WORKSHOPS
            ACTIVE BEFORE INSERT POSITION 0
            AS
            BEGIN
                IF (NEW.WORKSHOP_ID IS NULL) THEN
                    NEW.WORKSHOP_ID = NEXT VALUE FOR GEN_WORKSHOP_ID;
            END
        """)
        
        cur.execute("""
            CREATE TRIGGER CAMERAS_BI FOR CAMERAS
            ACTIVE BEFORE INSERT POSITION 0
            AS
            BEGIN
                IF (NEW.CAMERA_ID IS NULL) THEN
                    NEW.CAMERA_ID = NEXT VALUE FOR GEN_CAMERA_ID;
            END
        """)
        
        cur.execute("""
            CREATE TRIGGER REPORTS_BI FOR REPORTS
            ACTIVE BEFORE INSERT POSITION 0
            AS
            BEGIN
                IF (NEW.REPORT_ID IS NULL) THEN
                    NEW.REPORT_ID = NEXT VALUE FOR GEN_REPORT_ID;
            END
        """)
        
        con.commit()
        con.close()
        logger.info("БД создана успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании БД: {str(e)}")
        return False

def connect_database(path, user, password):
    """Подключение к существующей базе данных"""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database file not found: {path}")
    
    logger.info(f"Подключение к БД: {path}")
    try:
        # Используем тот же формат, что и при создании
        connection_string = f"localhost/3050:{path}"
        return fdb.connect(
            connection_string,
            user=user,
            password=password
        )
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {str(e)}")
        raise

def add_workshop(conn, workshop_number):
    """Добавление нового цеха в базу данных"""
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO WORKSHOPS (WORKSHOP_NUMBER) VALUES (?)", 
                    (workshop_number,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления цеха: {str(e)}")
        return False

def add_camera(conn, camera_id, workshop_id):
    """Добавление новой камеры в базу данных"""
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO CAMERAS (CAMERA_ID, WORKSHOP_ID) VALUES (?, ?)", 
                    (camera_id, workshop_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления камеры: {str(e)}")
        return False

def add_report(conn, camera_id, violation_time, violation_type, photo_path):
    """Добавление отчета о нарушении в базу данных"""
    try:
        with open(photo_path, 'rb') as f:
            photo_data = f.read()
        
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO REPORTS (CAMERA_ID, VIOLATION_TIME, VIOLATION_TYPE, PHOTO) "
            "VALUES (?, ?, ?, ?)",
            (camera_id, violation_time, violation_type, photo_data)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления отчета: {str(e)}")
        return False

def get_all_workshops(conn):
    """Получение списка всех цехов"""
    cur = conn.cursor()
    cur.execute("SELECT WORKSHOP_ID, WORKSHOP_NUMBER FROM WORKSHOPS")
    return cur.fetchall()

def get_workshop_by_camera(conn, camera_id):
    """Получение цеха по номеру камеры"""
    cur = conn.cursor()
    cur.execute("""
        SELECT w.WORKSHOP_NUMBER 
        FROM CAMERAS c
        JOIN WORKSHOPS w ON c.WORKSHOP_ID = w.WORKSHOP_ID
        WHERE c.CAMERA_ID = ?
    """, (camera_id,))
    result = cur.fetchone()
    return result[0] if result else None

def get_all_reports(conn):
    """Получение всех отчетов с информацией о цехе"""
    cur = conn.cursor()
    cur.execute("""
        SELECT r.REPORT_ID, r.CAMERA_ID, r.VIOLATION_TIME, r.VIOLATION_TYPE, w.WORKSHOP_NUMBER 
        FROM REPORTS r
        JOIN CAMERAS c ON r.CAMERA_ID = c.CAMERA_ID
        JOIN WORKSHOPS w ON c.WORKSHOP_ID = w.WORKSHOP_ID
        ORDER BY r.VIOLATION_TIME DESC
    """)
    return cur.fetchall()

def get_report_photo(conn, report_id):
    """Получение фото отчета по ID"""
    cur = conn.cursor()
    cur.execute("SELECT PHOTO FROM REPORTS WHERE REPORT_ID = ?", (report_id,))
    result = cur.fetchone()
    if result:
        # Читаем данные из BlobReader и преобразуем в байты
        blob_reader = result[0]
        photo_data = blob_reader.read()
        blob_reader.close()
        return photo_data
    else:
        return None
