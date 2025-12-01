FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY *.py .

# Создание директории для базы данных
RUN mkdir -p /app/data

# Запуск бота
CMD ["python", "bot.py"]
