from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

RUSSIAN_FONT_PATH = '/usr/share/fonts/liberation/LiberationMono-Regular.ttf'
RUSSIAN_FONT_BOLD_PATH = '/usr/share/fonts/liberation/LiberationMono-Bold.ttf'

def register_russian_fonts():
    """Регистрация русских шрифтов для использования в отчетах"""
    try:
        if os.path.exists(RUSSIAN_FONT_PATH):
            pdfmetrics.registerFont(TTFont('RussianFont', RUSSIAN_FONT_PATH))
        
        if os.path.exists(RUSSIAN_FONT_BOLD_PATH):
            pdfmetrics.registerFont(TTFont('RussianFont-Bold', RUSSIAN_FONT_BOLD_PATH))
        return True
    except Exception as e:
        print(f"Ошибка регистрации шрифтов: {str(e)}")
        return False

def generate_report_pdf(image_path, workshop_number, camera_id, violation_time, violation_type, output_path):
    """
    Генерация PDF отчета о нарушении
    
    Параметры:
    image_path - путь к изображению с нарушением
    workshop_number - номер цеха
    camera_id - ID камеры
    violation_time - время нарушения (строка)
    violation_type - тип нарушения
    output_path - путь для сохранения PDF
    """
    russian_fonts_registered = register_russian_fonts()
    
    font_normal = 'RussianFont' if russian_fonts_registered else 'Helvetica'
    font_bold = 'RussianFont-Bold' if russian_fonts_registered else 'Helvetica-Bold'
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName=font_bold,
        textColor=colors.red,
        fontSize=18,
        alignment=1,
        leading=20
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['BodyText'],
        fontName=font_normal,
        textColor=colors.black,
        fontSize=12,
        leading=14
    )
    
    # Заголовок отчета
    title = Paragraph("ОТЧЕТ О НАРУШЕНИИ СИЗ", title_style)
    title.wrap(width - 100, 50)
    title.drawOn(c, 50, height - 70)
    
    c.line(50, height - 90, width - 50, height - 90)
    
    info_items = [
        f"Цех: {workshop_number}",
        f"Камера: {camera_id}",
        f"Дата и время нарушения: {violation_time}",
        f"Тип нарушения: {violation_type}"
    ]
    
    y_position = height - 120
    for text in info_items:
        p = Paragraph(text, body_style)
        p.wrap(width - 100, 40)
        p.drawOn(c, 50, y_position)
        y_position -= 30
    
    try:
        img = ImageReader(image_path)
        img_width, img_height = img.getSize()
        aspect = img_height / float(img_width)
        
        display_width = min(400, width - 100)
        display_height = min(300, display_width * aspect)
        
        # Позиционируем изображение по центру
        x_pos = (width - display_width) / 2
        y_pos = y_position - display_height - 20
        
        if y_pos < 50:
            display_height = y_position - 70
            display_width = display_height / aspect
            x_pos = (width - display_width) / 2
        
        c.drawImage(
            img, 
            x_pos, 
            y_pos,
            width=display_width,
            height=display_height,
            mask='auto'
        )
    except Exception as e:
        print(f"Ошибка при добавлении изображения: {str(e)}")
        c.setFont(font_normal, 12)
        c.drawString(50, y_position - 30, "Изображение недоступно")
    
    c.setFont(font_normal, 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(width/2, 30, "Сгенерировано системой контроля СИЗ")
    
    c.save()