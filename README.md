📌 Описание

Школьный помощник - это телеграм-бот, созданный для помощи ученикам в обучении. Бот предоставляет следующие возможности:

Объяснение учебных тем

Генерация тестовых вопросов

Создание изображений по описанию

Калькулятор для вычислений

🛠 Технологии

Python 3.10

Библиотека telebot для работы с Telegram API

OpenAI API (через OpenRouter) для генерации текстовых ответов

FusionBrain API (Kandinsky 3.1) для генерации изображений

Pillow (PIL) для обработки изображений

🔑 Требуемые токены

Для работы бота необходимо создать файл config.py со следующими переменными:

TELEGRAM_TOKEN = "ваш_телеграм_токен"

AI_TOKEN = "ваш_openrouter_api_ключ"

FUSION_BRAIN_API_KEY = "ваш_fusionbrain_api_ключ"

FUSION_BRAIN_SECRET_KEY = "ваш_fusionbrain_secret_ключ"


🚀 Функционал

📚 Объяснение тем

Бот может объяснить любую школьную тему простым языком

После объяснения предлагает рекомендации для дальнейшего изучения

📝 Тесты

Выбор класса (1-11)

Выбор предмета (в зависимости от класса)

Генерация тестовых вопросов с 4 вариантами ответов

Проверка ответов и объяснение ошибок

🎨 Генерация изображений

Обычные изображения по описанию

Контурные рисунки (для обводки)

Выбор стиля (аниме, неон, 3D и др.)

🧮 Калькулятор

Полнофункциональный калькулятор с интерфейсом кнопок

Поддержка основных математических операций

🖼 Изображения

Бот использует два изображения:

hello.jpeg - приветственное изображение

info.jpeg - изображение для раздела "О боте"

⚙️ Установка и запуск

1. Установите зависимости:
pip install telebot requests pillow openai

2. Создайте файл config.py с необходимыми токенами

3. Запустите бота:
generate.py

📝 Примечание

Бот использует внешние API (OpenRouter и FusionBrain), поэтому для его работы необходимо подключение к интернету. В случае недоступности API бот уведомит пользователя об ошибке.

Для работы с генерацией изображений рекомендуется иметь стабильное интернет- соединение, так как процесс генерации может занимать до 2 минут.
