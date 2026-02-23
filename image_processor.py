#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


# Типы обработки
class ProcessingType(Enum):
    INVERT = "invert"      # Негатив
    BLUR = "blur"          # Размытие
    MIRROR = "mirror"      # Отражение


@dataclass
class ImageTask:
    """Задача на обработку"""
    task_id: int
    input_path: str
    output_path: str
    process_type: ProcessingType
    created_time: float


@dataclass
class TaskResult:
    """Результат обработки"""
    task_id: int
    success: bool
    message: str
    process_time: float
    consumer_id: int


class BlockingQueue:
    """Блокирующая очередь"""
    
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize)
        self.active = True
    
    def put(self, item):
        if not self.active:
            raise Exception("Очередь закрыта")
        self.queue.put(item)
        print(f"  [Queue] + Добавлен элемент. Очередь: {self.queue.qsize()}")
    
    def get(self):
        try:
            item = self.queue.get(timeout=0.1)
            print(f"  [Queue] - Извлечен элемент. Очередь: {self.queue.qsize()}")
            return item
        except queue.Empty:
            return None
    
    def task_done(self):
        self.queue.task_done()
    
    def close(self):
        self.active = False
    
    def size(self):
        return self.queue.qsize()


class Producer(threading.Thread):
    """Создатель задач"""
    
    def __init__(self, task_queue, images_folder, output_folder, 
                 process_type, num_images):
        super().__init__()
        self.task_queue = task_queue
        self.images_folder = images_folder
        self.output_folder = output_folder
        self.process_type = process_type
        self.num_images = num_images
        self.running = True
        self.tasks_created = 0
        
        os.makedirs(output_folder, exist_ok=True)
        print("[PRODUCER] Создан")
    
    def run(self):
        print("\n[PRODUCER] НАЧАЛО РАБОТЫ")
        
        # Получаем список изображений
        try:
            all_images = [f for f in os.listdir(self.images_folder) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        except FileNotFoundError:
            print("[PRODUCER] ОШИБКА: Папка не найдена!")
            return
        
        if not all_images:
            print("[PRODUCER] Нет изображений!")
            return
        
        print(f"[PRODUCER] Найдено изображений: {len(all_images)}")
        
        # Создаем задачи
        for i in range(self.num_images):
            if not self.running:
                break
            
            # Выбираем случайное изображение
            image_file = random.choice(all_images)
            input_path = os.path.join(self.images_folder, image_file)
            
            # Имя выходного файла
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
            
            # Отправляем в очередь
            print(f"[PRODUCER] Задача #{i}: {image_file}")
            self.task_queue.put(task)
            self.tasks_created += 1
            
            # Небольшая задержка
            time.sleep(0.3)
        
        print(f"[PRODUCER] ЗАВЕРШЕНИЕ: создано {self.tasks_created} задач")
    
    def stop(self):
        self.running = False


class Consumer(threading.Thread):
    """Обработчик задач"""
    
    def __init__(self, consumer_id, task_queue, result_queue):
        super().__init__()
        self.consumer_id = consumer_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.running = True
        self.processed_count = 0
        print(f"[Consumer-{consumer_id}] Создан")
    
    def run(self):
        print(f"\n[Consumer-{self.consumer_id}] НАЧАЛО РАБОТЫ")
        
        while self.running:
            # Получаем задачу
            task = self.task_queue.get()
            
            if task is None:
                continue
            
            # Обрабатываем
            print(f"[Consumer-{self.consumer_id}] Обработка задачи #{task.task_id}")
            start_time = time.time()
            success, message = self.process_image(task)
            process_time = time.time() - start_time
            
            # Создаем результат
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
