FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей и шрифтов
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY *.py ./

# Создание директории для базы данных
RUN mkdir -p /app/data

# Запуск бота
CMD ["python", "bot.py"]
