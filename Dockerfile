# Используем официальный Python образ
FROM python:3.9-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем зависимости
COPY requirements.txt /app/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . /app/

# Выполняем миграции, создаем суперпользователя и запускаем сервер
CMD ["sh", "-c", "python manage.py migrate && python manage.py migrations && python manage.py shell -c \"from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin')\" && python manage.py runserver 0.0.0.0:8000"]
