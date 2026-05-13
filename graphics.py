import io
from PIL import Image, ImageDraw, ImageFont

def create_hacking_image(mission_name: str, hint: str, nmap_done: bool = True) -> io.BytesIO:
    """Генерирует статичный баннер терминала хакера."""
    width, height = 600, 250
    img = Image.new('RGB', (width, height), color=(15, 15, 15))
    draw = ImageDraw.Draw(img)
    
    # Пытаемся загрузить системные шрифты, иначе берем дефолтный
    try:
        font = ImageFont.truetype("consola.ttf", 20)
        title_font = ImageFont.truetype("consola.ttf", 28)
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            title_font = ImageFont.truetype("arial.ttf", 28)
        except IOError:
            font = ImageFont.load_default()
            title_font = font

    # Рисуем сканлайны (эффект старого монитора)
    for y in range(0, height, 4):
        draw.line([(0, y), (width, y)], fill=(0, 25, 0), width=1)
        
    # Заголовки
    draw.text((20, 20), f"> СОЕДИНЕНИЕ УСТАНОВЛЕНО", fill=(0, 255, 0), font=title_font)
    draw.text((20, 60), f"ЦЕЛЬ: {mission_name}", fill=(0, 200, 0), font=font)
    
    # Подсказка (желтым)
    y_offset = 90
    draw.text((20, y_offset), "ДАННЫЕ:", fill=(200, 200, 0), font=font)
    
    import textwrap
    
    if not nmap_done:
        draw.text((120, y_offset), "[ЗАШИФРОВАНО] Введи: nmap", fill=(255, 100, 0), font=font)
    else:
        # Разбиваем текст по словам на строки длиной до 38 символов
        hint_lines = textwrap.wrap(hint, width=38)
        for line in hint_lines:
            draw.text((120, y_offset), line, fill=(200, 200, 0), font=font)
            y_offset += 25
            
    # Сохраняем в BytesIO для отправки в Telegram
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio
