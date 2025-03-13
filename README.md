📌 WebAdminDB – Веб-интерфейс для администрирования баз данных.
Проект помогает производить администрирование БД через веб интерфейс. Что необходимо сделать, это подключиться к БД и начать работу...


## 🚀 Развитие проекта – Ищем участников!  
Этот проект создается **для развития** и мы ищем **разработчиков, энтузиастов и единомышленников**, которые хотят участвовать в создании полезного инструмента для тестирования и анализа данных.  
🔹 Если вам **интересна работа с данными**, **OCR**, **разработка API**, **интерфейсов** или **алгоритмов генерации данных**, присоединяйтесь к проекту!  
🤝 Вклад
Если хотите помочь развитию проекта:
Сделайте fork репозитория
Создайте feature-branch (git checkout -b new-feature)
Внесите изменения и зафиксируйте их (git commit -m "Добавлена новая фича")
Отправьте изменения (git push origin new-feature)
Создайте Pull Request


## 📥 Установка  
Создайте файл ".env" и укажите необходимые настройки -
# Подключение к базе данных
POSTGRES_DB=name_db
POSTGRES_USER=user_db
POSTGRES_PASSWORD=pass_db
DB_HOST=localhost
DB_PORT=5432
DB_ATOMIC_REQUESTS=False
DB_CONN_HEALTH_CHECKS=False
DB_CONN_MAX_AGE=0
DB_AUTOCOMMIT=True
# Отправка уведомлений на электронную почту
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=...........mail.com
EMAIL_HOST_PASSWORD=..................
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

## 🎥 Видео-обзор проекта
Посмотрите демонстрацию работы проекта на YouTube:
(https://youtu.be/5QQ1RjDKR2k)

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver



