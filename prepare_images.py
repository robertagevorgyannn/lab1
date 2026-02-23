"""
prepare_images.py
Скрипт для создания тестовых изображений
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_images():
    """Создание набора тестовых изображений"""
    
    print("Создаю тестовые изображения...")
    
    # Создаем папку для входных изображений
    if not os.path.exists("input_images"):
        os.makedirs("input_images")
        print("Создана папка 'input_images'")
    
    # Создаем 6 разных изображений
    for i in range(1, 7):
        # Создаем новое изображение размером 300x200
        img = Image.new('RGB', (300, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Рисуем разные фигуры в зависимости от номера
        if i == 1:
            # Красный квадрат
            draw.rectangle([50, 30, 250, 170], fill='red')
            draw.text((120, 90), "Image 1", fill='white')
            
        elif i == 2:
            # Синий круг
            draw.ellipse([50, 30, 250, 170], fill='blue')
            draw.text((120, 90), "Image 2", fill='white')
            
        elif i == 3:
            # Зеленый треугольник
            draw.polygon([(150, 30), (50, 170), (250, 170)], fill='green')
            draw.text((120, 100), "Image 3", fill='white')
            
        elif i == 4:
            # Разноцветные полосы
            colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
            for j, color in enumerate(colors):
                draw.rectangle([50, 30 + j*23, 250, 53 + j*23], fill=color)
            draw.text((120, 90), "Image 4", fill='black')
            
        elif i == 5:
            # Желтый прямоугольник с рамкой
            draw.rectangle([40, 20, 260, 180], fill='yellow', outline='black', width=3)
            draw.text((120, 90), "Image 5", fill='black')
            
        else:
            # Градиент серого
            for x in range(300):
                for y in range(200):
                    gray = int((x/300 + y/200) * 255 / 2)
                    img.putpixel((x, y), (gray, gray, gray))
            draw = ImageDraw.Draw(img)
            draw.text((120, 90), "Image 6", fill='red')
        
        # Сохраняем изображение
        filename = f"input_images/test_{i}.png"
        img.save(filename)
        print(f"  Создано: {filename}")
    
    print("\nГотово! Создано 6 тестовых изображений в папке 'input_images'")

if __name__ == "__main__":
    create_test_images()
