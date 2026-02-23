#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading #модуль для многопоточности - позволяет создавать и управлять потоками. нужен для параллельной обработки нескольких изобр.
import queue #потокобезопасная очередь для передачи задач между потоками. производители кладут задачи, потребители забирают. FIFO 
import os #работа с os - для работы с файловой системой: проверка существования файлов, создание папок, пути
import time #для задержек, измерения времени выполнения, создания временных меток 
from PIL import Image, ImageFilter #импортируем из библиотеки обработки изображений основной класс Image - открыть, сохранить, преобразовать изображения
#ImageFilter - применять эффекты (размытие и тд) 
from dataclasses import dataclass #декоратор для классов данных - автоматически генерирует __init__, __repr__ и другие методы для классов, которые в основном хранят данные
from enum import Enum #для создания ограниченного набора констант (типы обработки) 
import random #для выбора случайных изображений
from datetime import datetime #работа с датой/временем - для логирования, временных меток, измерения времени выполнения

#варианты обработки изображений
class ProcessingType(Enum):
    INVERT = "invert"      #инверсия
    BLUR = "blur"          #размытие
    MIRROR = "mirror"      #отражение

@dataclass #Python автоматически создает конструктор и другие методы при наличии декоратора 
class ImageTask: #представляет одну задачу на обработку
    task_id: int #id задачи 
    input_path: str #путь к исходному файлу - откуда брать изображения
    output_path: str #путь для результата - куда сохранить обработанное изображение
    process_type: ProcessingType #вариант обработки
    created_time: float #время создания

@dataclass
class TaskResult: #хранит информацию о результате обработки одной задачи 
    task_id: int
    success: bool #флаг успеха 
    message: str #текстовое сообщение (описание ошибки или "успешно")
    process_time: float
    consumer_id: int

class BlockingQueue: #класс для расширения стандартной очереди queue.Queue добавляя флаг активности, логирование 
    def __init__(self, maxsize=0): #self - ссылка на создаваемый объект, параметр со значением по умолчанию 0
        self.queue = queue.Queue(maxsize)  #создание внутренней очереди, self.queue - создает атрибут объекта с именем queue
        #queue.Queue - обращается к классу Queue из импортированного модуля queue, (maxsize) - передает параметр размера в конструктор Queue 
        self.active = True #установка флага активности - создает атрибут active со значение True. Очередь изначально открыта
    
    def put(self, item): #определение метода put для добавления элемента， item - параметр， элемент для добавления в очередь
        if not self.active:
            raise Exception("Очередь закрыта")
        self.queue.put(item) #self.queue - обращение к внутренней очереди, put(item) - вызов метода put стандартной очереди
        #элемент добавляется в очередь (блокирующая операция если очередь полна)
        print(f"  [Queue] + Добавлен элемент. Очередь: {self.queue.qsize()}") 
     
    def get(self):  #определение метода get для извлечения элемента
        try:
            item = self.queue.get(timeout=0.1) #метод извлечения из очереди, ждать не больше 0.1 секунды если очередь пуста
            print(f"  [Queue] - Извлечен элемент. Очередь: {self.queue.qsize()}") 
            return item
        except queue.Empty: #если вдруг очередь пуста, то выводится ошибка и никакой элемент не возвращается
            return None
    
    def task_done(self): #для отметки о выполнении задачи 
        self.queue.task_done() #вызов метода внутренней очереди - сообщает, что обработки задачи завершена 
    
    def close(self):
        self.active = False #установка флага активности в False - после этого вызов put() будет выбрасывать исключение. существующие элементы можно всё еще можно получить
    
    def size(self):
        return self.queue.qsize() 


class Producer(threading.Thread): #создается класс Producer, который наследуется от threading.Thread, значит, каждый объект Producer будет работать в отдельном потоке 
    
    def __init__(self, task_queue, images_folder, output_folder, 
                 process_type, num_images):
        super().__init__() #вызов конструктора родительского класса 
        self.task_queue = task_queue #запоминается ссылка на очередь задач в атрибуте объекта
        self.images_folder = images_folder #сохранение папки с исходниками
        self.output_folder = output_folder #сохранение папки для результатов 
        self.process_type = process_type #сохранение типа обработки
        self.num_images = num_images #количество изображений для обработки
        self.running = True #флаг работы
        self.tasks_created = 0 #счетчик созданных задач
        
        os.makedirs(output_folder, exist_ok=True) #создание всех папок по пути если их нет, exist_ok=True - не выдаёт ошибку, если папка уже существует
        print("[PRODUCER] Создан") #отладочный вывод - сообщает о создании производителя
    
    def run(self): #метод run() - переопределяет метод родительского класса Thread, когда вызывается start(), этот код выполняется в новом потоке. 
        print("\n[PRODUCER] НАЧАЛО РАБОТЫ")
        
        #получаем список изображений
        try:
            all_images = [f for f in os.listdir(self.images_folder) #перебирает каждый файл из списка всех файлов в папке
                         if f.lower().endswith(('.png', '.jpg', '.jpeg'))] #проверяет расширение
                         #переводит имя файла в нижний регистр
        except FileNotFoundError:
            print("[PRODUCER] ОШИБКА: Папка не найдена!")
            return
        
        if not all_images: #если изображений не найдено 
            print("[PRODUCER] Нет изображений!")
            return
        
        print(f"[PRODUCER] Найдено изображений: {len(all_images)}") #сообщает сколько изображений найдено в папке 
        
        #создаем задачи
        for i in range(self.num_images):
            if not self.running: #если self.running стал False 
                break #выходим из цикла
            
            #выбираем случайное изображение
            image_file = random.choice(all_images)
            input_path = os.path.join(self.images_folder, image_file) #формирование полного пути к исходному файлу 
            #         соединяет части пути/папка с исходниками/имя выбранного файла
            
            #имя выходного файла
            name, ext = os.path.splitext(image_file) #разбиение имени файла на 2 части - имя файла без расширения/расширение с точкой
            timestamp = datetime.now().strftime("%H%M%S") #создание временной метки
            output_name = f"{name}_{self.process_type.value}_{i}_{timestamp}{ext}" #формирование имени выходного файла
            #            имя файла/     тип обработки    /номер задачи/дата создания/расширение
            output_path = os.path.join(self.output_folder, output_name) #полный путь к выходному файлу 
            
            #создаем задачу
            task = ImageTask(
                task_id=i,
                input_path=input_path,
                output_path=output_path,
                process_type=self.process_type,
                created_time=time.time()
            )
            
            #отправляем в очередь
            print(f"[PRODUCER] Задача #{i}: {image_file}")
            self.task_queue.put(task) # отправка в очередь -> помещает созданную задачу в общую очередь
            self.tasks_created += 1
            
            #небольшая задержка
            time.sleep(0.3)
        
        print(f"[PRODUCER] ЗАВЕРШЕНИЕ: создано {self.tasks_created} задач")
    
    def stop(self):
        self.running = False


class Consumer(threading.Thread):  #создает класс Consumer, каждый будет работать в отдельном потоке и обрабатывать изображения
    def __init__(self, consumer_id, task_queue, result_queue):
        super().__init__()
        self.consumer_id = consumer_id
        self.task_queue = task_queue #очередь задач - откуда брать изображения на обработку
        self.result_queue = result_queue #очередь результатов 
        self.running = True
        self.processed_count = 0
        print(f"[Consumer-{consumer_id}] Создан")
    
    def run(self):
        print(f"\n[Consumer-{self.consumer_id}] НАЧАЛО РАБОТЫ")
        
        while self.running:
            #получаем задачу
            task = self.task_queue.get()
            
            if task is None:
                continue
            
            #обрабатываем
            print(f"[Consumer-{self.consumer_id}] Обработка задачи #{task.task_id}") 
            #логирование - сообщает, какой потребитель начал обрабатывать какую задачу 
            start_time = time.time() #засекаем время начала 
            success, message = self.process_image(task) #вызывается метод process_image - передает задачу - получает 2 значения
            process_time = time.time() - start_time # вычисление времени обработки
            
            #создаем результат
            result = TaskResult(
                task_id=task.task_id,
                success=success,
                message=message,
                process_time=process_time,
                consumer_id=self.consumer_id
            )
            
            # Отправляем результат
            self.result_queue.put(result)
            self.task_queue.task_done()
            self.processed_count += 1
            
            status = "✓" if success else "✗"
            print(f"[Consumer-{self.consumer_id}] Задача #{task.task_id} {status} за {process_time:.2f}с")
        
        print(f"[Consumer-{self.consumer_id}] ЗАВЕРШЕНИЕ: обработано {self.processed_count}")
    
    def process_image(self, task):
        """Обработка изображения"""
        try:
            # Открываем изображение
            with Image.open(task.input_path) as img:
                # Применяем эффект
                if task.process_type == ProcessingType.INVERT:
                    # Инверсия (негатив)
                    if img.mode == 'RGB':
                        processed = Image.eval(img, lambda x: 255 - x)
                    else:
                        img_rgb = img.convert('RGB')
                        processed = Image.eval(img_rgb, lambda x: 255 - x)
                
                elif task.process_type == ProcessingType.BLUR:
                    # Размытие
                    processed = img.filter(ImageFilter.GaussianBlur(radius=2))
                
                elif task.process_type == ProcessingType.MIRROR:
                    # Отражение
                    processed = img.transpose(Image.FLIP_LEFT_RIGHT)
                
                else:
                    return False, f"Неизвестный тип: {task.process_type}"
                
                # Сохраняем
                processed.save(task.output_path)
            
            return True, f"Сохранено: {task.output_path}"
        
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
    
    def stop(self):
        self.running = False


class ResultCollector:
    """Сборщик результатов"""
    
    def __init__(self, result_queue, num_expected):
        self.result_queue = result_queue
        self.num_expected = num_expected
        self.results = []
        self.running = True
    
    def collect(self):
        """Сбор результатов"""
        print("\n[COLLECTOR] Начинаю сбор результатов")
        
        while len(self.results) < self.num_expected:
            result = self.result_queue.get()
            if result:
                self.results.append(result)
                print(f"[COLLECTOR] Получен результат задачи #{result.task_id}")
        
        print("[COLLECTOR] Сбор завершен")
    
    def print_stats(self):
        """Вывод статистики"""
        print("\n" + "="*60)
        print("СТАТИСТИКА ОБРАБОТКИ")
        print("="*60)
        
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        print(f"Всего задач: {len(self.results)}")
        print(f"Успешно: {successful}")
        print(f"Ошибок: {failed}")
        
        if self.results:
            total_time = sum(r.process_time for r in self.results)
            avg_time = total_time / len(self.results)
            print(f"Общее время: {total_time:.2f}с")
            print(f"Среднее время: {avg_time:.2f}с")
        
        print("\nДетали по задачам:")
        print("-" * 60)
        for r in self.results:
            status = "✓" if r.success else "✗"
            print(f"[{status}] Задача #{r.task_id}: Consumer-{r.consumer_id} - {r.process_time:.2f}с")
            if not r.success:
                print(f"      Ошибка: {r.message}")


def main():
    """Главная функция"""
    
    print("="*60)
    print("ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА ИЗОБРАЖЕНИЙ")
    print("Шаблон Producer-Consumer")
    print("="*60)
    
    # НАСТРОЙКИ
    INPUT_FOLDER = "input_images"
    OUTPUT_FOLDER = "output_images"
    NUM_TASKS = 10           # Количество задач
    NUM_CONSUMERS = 3        # Количество потребителей
    
    # Выбираем тип обработки
    print("\nВыберите тип обработки:")
    print("1 - Инверсия (негатив)")
    print("2 - Размытие")
    print("3 - Отражение")
    
    choice = input("Ваш выбор (1-3): ").strip()
    
    if choice == "1":
        process_type = ProcessingType.INVERT
        print("Выбрана: ИНВЕРСИЯ")
    elif choice == "2":
        process_type = ProcessingType.BLUR
        print("Выбрано: РАЗМЫТИЕ")
    elif choice == "3":
        process_type = ProcessingType.MIRROR
        print("Выбрано: ОТРАЖЕНИЕ")
    else:
        print("Неверный выбор. Использую ИНВЕРСИЮ")
        process_type = ProcessingType.INVERT
    
    # Создаем очереди
    task_queue = BlockingQueue(maxsize=5)     # Очередь задач
    result_queue = BlockingQueue(maxsize=20)  # Очередь результатов
    
    # Создаем producer
    producer = Producer(task_queue, INPUT_FOLDER, OUTPUT_FOLDER, 
                       process_type, NUM_TASKS)
    
    # Создаем consumers
    consumers = []
    for i in range(NUM_CONSUMERS):
        consumer = Consumer(i + 1, task_queue, result_queue)
        consumers.append(consumer)
    
    # Создаем collector
    collector = ResultCollector(result_queue, NUM_TASKS)
    
    # ЗАПУСК
    print("\n" + "="*60)
    print("ЗАПУСК ПОТОКОВ")
    print("="*60)
    
    # Запускаем producer
    producer.start()
    
    # Запускаем consumers
    for consumer in consumers:
        consumer.start()
    
    # Ждем завершения producer
    producer.join()
    print("\n[MAIN] Producer завершил работу")
    
    # Ждем пока очередь задач опустеет
    time.sleep(2)
    
    # Останавливаем consumers
    print("\n[MAIN] Останавливаем consumers...")
    for consumer in consumers:
        consumer.stop()
    
    # Ждем завершения consumers
    for consumer in consumers:
        consumer.join()
    
    # Собираем результаты
    collector.collect()
    
    # Выводим статистику
    collector.print_stats()
    
    print("\n" + "="*60)
    print("ПРОГРАММА ЗАВЕРШЕНА")
    print(f"Результаты сохранены в папке: {OUTPUT_FOLDER}")
    print("="*60)


if __name__ == "__main__":
    main()
