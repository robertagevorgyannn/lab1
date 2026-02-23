"""
image_processor.py
Параллельная обработка изображений с использованием паттерна Producer-Consumer
"""

import threading
import queue
import os
import time
from PIL import Image, ImageFilter
from dataclasses import dataclass
from enum import Enum
import random
from datetime import datetime


# Типы обработки изображений
class ProcessingType(Enum):
    INVERT = "invert"      # Инверсия цветов (негатив)
    BLUR = "blur"          # Размытие
    MIRROR = "mirror"      # Отражение по горизонтали


@dataclass
class ImageTask:
    """Класс для задачи на обработку изображения"""
    task_id: int
    input_path: str
    output_path: str
    process_type: ProcessingType
    created_time: float


@dataclass
class TaskResult:
    """Класс для результата обработки"""
    task_id: int
    success: bool
    message: str
    process_time: float
    consumer_id: int


class BlockingQueue:
    """
    Блокирующая очередь для паттерна Producer-Consumer
    Обеспечивает безопасную передачу данных между потоками
    """
    
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize)
        self.active = True
    
    def put(self, item):
        """Положить элемент в очередь (блокируется если очередь полна)"""
        if not self.active:
            raise Exception("Очередь закрыта")
        self.queue.put(item)
        print(f"  [Queue] Добавлен элемент. Размер очереди: {self.queue.qsize()}")
    
    def get(self):
        """Получить элемент из очереди (блокируется если очередь пуста)"""
        try:
            # Используем таймаут для возможности проверки завершения
            item = self.queue.get(timeout=0.1)
            print(f"  [Queue] Извлечен элемент. Размер очереди: {self.queue.qsize()}")
            return item
        except queue.Empty:
            return None
    
    def task_done(self):
        """Отметить что задача обработана"""
        self.queue.task_done()
    
    def close(self):
        """Закрыть очередь для новых элементов"""
        self.active = False
    
    def size(self):
        """Текущий размер очереди"""
        return self.queue.qsize()


class Producer(threading.Thread):
    """
    Producer - создает задачи на обработку изображений
    Наследуется от threading.Thread для работы в отдельном потоке
    """
    
    def __init__(self, task_queue, images_folder, output_folder, 
                 process_type, num_images, producer_id=1):
        super().__init__()
        self.task_queue = task_queue
        self.images_folder = images_folder
        self.output_folder = output_folder
        self.process_type = process_type
        self.num_images = num_images
        self.producer_id = producer_id
        self.running = True
        self.tasks_created = 0
        
        # Создаем папку для результатов если её нет
        os.makedirs(output_folder, exist_ok=True)
        print(f"[Producer-{producer_id}] Инициализирован")
    
    def run(self):
        """Основной метод потока - выполняется при start()"""
        print(f"\n[Producer-{self.producer_id}] НАЧАЛО РАБОТЫ")
        print(f"[Producer-{self.producer_id}] Буду создавать {self.num_images} задач")
        
        # Получаем список всех изображений в папке
        try:
            all_images = [f for f in os.listdir(self.images_folder) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        except FileNotFoundError:
            print(f"[Producer-{self.producer_id}] ОШИБКА: Папка {self.images_folder} не найдена!")
            return
        
        if not all_images:
            print(f"[Producer-{self.producer_id}] ВНИМАНИЕ: В папке нет изображений!")
            return
        
        print(f"[Producer-{self.producer_id}] Найдено изображений: {len(all_images)}")
        
        # Создаем задачи
        for i in range(self.num_images):
            if not self.running:
                break
            
            # Выбираем случайное изображение
            image_file = random.choice(all_images)
            input_path = os.path.join(self.images_folder, image_file)
            
            # Создаем имя выходного файла
            name, ext = os.path.splitext(image_file)
            timestamp = datetime.now().strftime("%H%M%S")
            output_name = f"{name}_{self.process_type.value}_{i}_{timestamp}{ext}"
            output_path = os.path.join(self.output_folder, output_name)
            
            # Создаем задачу
            task = ImageTask(
                task_id=i,
                input_path=input_path,
                output_path=output_path,
                process_type=self.process_type,
                created_time=time.time()
            )
            
            # Отправляем в очередь (блокируется если очередь полна)
            print(f"[Producer-{self.producer_id}] Создаю задачу #{i}: {image_file} -> {output_name}")
            self.task_queue.put(task)
            self.tasks_created += 1
            
            #
