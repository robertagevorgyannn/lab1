from PIL import Image, ImageDraw, ImageFont 
#Image - основной класс для работы с изоражениями (создание,хранение) 
#ImageDraw - инструмент для рисования на изображениях (фигуры, текст)
import os #для работы с файловой системой (проверка существования папки, создание папки)

def create_test_images():
    print("Создаю тестовые изображения...")
    
    #создаем папку для входных изображений
    if not os.path.exists("input_images"): #проверка существования папки input_images 
        #true если путь существует, false если нет 
        os.makedirs("input_images") #создание директории input_images
        print("Создана папка 'input_images'")
    
    #создаем 6 разных изображений
    for i in range(1, 7):
        img = Image.new('RGB', (300, 200), color='white') 
        draw = ImageDraw.Draw(img)
        
        #рисуем разные фигуры в зависимости от номера
        if i == 1:
            #красный квадрат
            draw.rectangle([50, 30, 250, 170], fill='red')
            draw.text((120, 90), "Image 1", fill='white')
            
        elif i == 2:
            #синий круг
            draw.ellipse([50, 30, 250, 170], fill='blue')
            draw.text((120, 90), "Image 2", fill='white')
            
        elif i == 3:
            #зеленый треугольник
            draw.polygon([(150, 30), (50, 170), (250, 170)], fill='green')
            draw.text((120, 100), "Image 3", fill='white')
            
        elif i == 4:
            #разноцветные полосы
            colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
            for j, color in enumerate(colors):
                draw.rectangle([50, 30 + j*23, 250, 53 + j*23], fill=color)
            draw.text((120, 90), "Image 4", fill='black')
            
        elif i == 5:
            #желтый прямоугольник с рамкой
            draw.rectangle([40, 20, 260, 180], fill='yellow', outline='black', width=3)
            draw.text((120, 90), "Image 5", fill='black')
            
        else:
            #градиент серого
            for x in range(300):
                for y in range(200):
                    gray = int((x/300 + y/200) * 255 / 2)
                    img.putpixel((x, y), (gray, gray, gray))
            draw = ImageDraw.Draw(img)
            draw.text((120, 90), "Image 6", fill='red')
        
        #сохраняем изображение
        filename = f"input_images/test_{i}.png" #формирование имени файла 
        #f-строка (formatted string) - подставляет значение i
        #Пример: при i=1 получится "input_images/test_1.png"
        img.save(filename) #сохранение изображения в файл
        print(f"  Создано: {filename}")
    
    print("\nСоздано 6 тестовых изображений в папке 'input_images'")

if __name__ == "__main__": #проверка если файл запущен напрямую, а не импортирован как модуль
    create_test_images()
