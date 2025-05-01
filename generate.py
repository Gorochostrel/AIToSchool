import base64
import json
import re
import time
from io import BytesIO

import requests
import telebot
from PIL import Image
from openai import OpenAI
from telebot import types

from config import TELEGRAM_TOKEN, AI_TOKEN, FUSION_BRAIN_API_KEY, FUSION_BRAIN_SECRET_KEY

bot = telebot.TeleBot(TELEGRAM_TOKEN)

ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=AI_TOKEN,
    default_headers={
        "HTTP-Referer": "https://github.com/yourusername/school-helper-bot",
        "X-Title": "School Quiz Bot",
    }
)

GRADE_SUBJECTS = {
    1: ["математика", "русский язык", "окружающий мир", "чтение", "рисование", "музыка", "технология", "физкультура"],
    2: ["математика", "русский язык", "окружающий мир", "английский язык", "китайский язык", "чтение", "рисование",
        "музыка", "технология", "физкультура"],
    3: ["математика", "русский язык", "окружающий мир", "литературное чтение", "английский язык", "китайский язык",
        "музыка", "ИЗО", "технология", "физкультура", "ОРКСЭ"],
    4: ["математика", "русский язык", "окружающий мир", "литературное чтение", "английский язык", "китайский язык",
        "музыка", "ИЗО", "технология", "физкультура", "ОРКСЭ", "информатика"],
    5: ["математика", "русский язык", "история", "биология", "литература", "английский язык", "география",
        "китайский язык", "музыка", "ИЗО", "технология", "физкультура", "обществознание"],
    6: ["математика", "русский язык", "история", "биология", "литература", "английский язык", "география",
        "китайский язык", "музыка", "ИЗО", "технология", "физкультура", "обществознание"],
    7: ["математика", "физика", "химия", "биология", "литература", "русский язык", "геометрия", "английский язык",
        "ОБЖ", "история", "география", "китайский язык", "информатика", "обществознание", "технология", "физкультура",
        "ИЗО"],
    8: ["математика", "физика", "химия", "биология", "литература", "русский язык", "геометрия", "английский язык",
        "ОБЖ", "история", "география", "китайский язык", "информатика", "обществознание", "технология", "физкультура",
        "черчение"],
    9: ["математика", "физика", "химия", "биология", "информатика", "литература", "русский язык", "геометрия",
        "английский язык", "ОБЖ", "история", "география", "китайский язык", "обществознание", "экономика", "право",
        "астрономия"],
    10: ["математика", "физика", "химия", "биология", "информатика", "обществознание", "литература", "русский язык",
         "геометрия", "английский язык", "ОБЖ", "история", "география", "китайский язык", "экономика", "право",
         "астрономия", "естествознание"],
    11: ["математика", "физика", "химия", "биология", "информатика", "обществознание", "литература", "русский язык",
         "геометрия", "английский язык", "ОБЖ", "история", "география", "китайский язык", "экономика", "право",
         "астрономия", "естествознание", "МХК"]
}


class FusionBrainAPI:
    def __init__(self):
        self.API_URL = "https://api-key.fusionbrain.ai/key/api/v1/"
        self.AUTH_HEADERS = {
            'X-Key': f'Key {FUSION_BRAIN_API_KEY}',
            'X-Secret': f'Secret {FUSION_BRAIN_SECRET_KEY}',
        }
        self.MODEL_ID = self._get_model_id()
        self.STYLES = self._get_available_styles()
        self.COOSHEN_ID = self._get_available_styles()

    def _get_model_id(self):
        try:
            response = requests.get(
                self.API_URL + 'pipelines',
                headers=self.AUTH_HEADERS,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data[0]['id']
        except Exception as e:
            print(f"Error getting model ID: {str(e)}")
            return None

    @staticmethod
    def _get_available_styles():
        return ["DEFAULT", "UHD", "ANIME", "NEON", "DETAILED", "KANDINSKY", "3D_MODEL", "WATERCOLOR"]

    def generate(self, prompt, style="DEFAULT", width=1024, height=1024, negative_prompt=None):
        if not self.MODEL_ID:
            return None

        params = {
            "type": "GENERATE",
            "numImages": 1,
            "width": width,
            "height": height,
            "generateParams": {
                "query": prompt
            }
        }

        if style != "DEFAULT":
            params["style"] = style

        if negative_prompt:
            params["negativePromptDecoder"] = negative_prompt

        data = {
            'pipeline_id': (None, self.MODEL_ID),
            'params': (None, json.dumps(params), 'application/json')
        }

        try:
            response = requests.post(
                self.API_URL + 'pipeline/run',
                headers=self.AUTH_HEADERS,
                files=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['uuid']
        except Exception as e:
            print(f"Generation error: {str(e)}")
            return None

    def check_generation_status(self, request_id, attempts=15, delay=10):
        for _ in range(attempts):
            try:
                response = requests.get(
                    self.API_URL + 'pipeline/status/' + request_id,
                    headers=self.AUTH_HEADERS,
                    timeout=10
                )
                data = response.json()

                if data['status'] == 'DONE':
                    return data['result']['files'][0] if data.get('result', {}).get('files') else None
                elif data['status'] == 'FAIL':
                    print(f"Generation failed: {data.get('errorDescription', 'Unknown error')}")
                    return None

                time.sleep(delay)
            except Exception as e:
                print(f"Status check error: {str(e)}")
                time.sleep(delay)
        return None


try:
    fusion_api = FusionBrainAPI()
except Exception as e:
    print(f"FusionBrainAPI init error: {str(e)}")
    fusion_api = None


def format_text(text):
    text = text.replace('###', '-')
    parts = text.split('**')
    for i in range(1, len(parts), 2):
        parts[i] = f'<b>{parts[i]}</b>'
    return ''.join(parts)


def generate_ai_question(grade, subject, max_attempts=5):
    prompt = f"""
    Сгенерируй вопрос для {grade} класса по предмету "{subject}" в формате:
    "текствопроса_ответ1_ответ2_ответ3_ответ4_номерправильногоответа"

    Правила:
    1. Только 4 варианта ответа
    2. Номер правильного ответа (1-4)
    3. Разделяй части подчеркиванием
    4. Без кавычек
    5. Пример: Сколько будет 2+2?_4_5_6_7_1
    """

    for attempt in range(max_attempts):
        try:
            response = ai_client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.5,
                max_tokens=200
            )
            question_data = response.choices[0].message.content.strip()

            if validate_question(question_data):
                return question_data

        except Exception as e:
            print(f"Question generation error: {e}")

        time.sleep(1)
    return None


def validate_question(question):
    parts = question.split('_')
    return len(parts) == 6 and parts[5] in ['1', '2', '3', '4']


def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('📚 Объяснить тему'),
        types.KeyboardButton('📝 Тест'),
        types.KeyboardButton('🎨 Генерация изображений'),
        types.KeyboardButton('🧮 Калькулятор'),
        types.KeyboardButton('ℹ️ О боте')
    ]
    markup.add(*buttons)
    return markup


def add_back_button(markup):
    markup.add(types.KeyboardButton('🔙 На главную'))
    return markup


def generate_recommendations(topic):
    prompt = f"""
    На основе темы "{topic}" сгенерируй 2 рекомендации для дальнейшего изучения.
    Формат: перваярекомендация_втораярекомендация
    Без кавычек, разделяй подчеркиванием.
    Пример: тебе до этого задали Дроби как тему и ты должен в своем сообщении написать "Что такое знаменатель_Десятичные дроби"
    """

    try:
        response = ai_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        recommendations = response.choices[0].message.content.strip()
        if '_' in recommendations and len(recommendations.split('_')) == 2:
            return recommendations
    except:
        pass
    return "узнать больше по этой теме_изучить смежные темы"


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        with open('hello.jpeg', 'rb') as photo:
            bot.send_photo(message.chat.id, photo)
    except:
        pass

    text = format_text("""
    👋 Привет! Я - твой школьный ИИ помощник

    📚 Могу объяснить любую тему
    📝 Проверить твои знания
    🎨 Создать изображение по описанию
    🧮 Произвести вычисления

    Выбери действие:
    """)

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=create_main_menu(),
        parse_mode='HTML'
    )


@bot.message_handler(func=lambda m: m.text == 'ℹ️ О боте')
def about_bot(message):
    try:
        with open('info.jpeg', 'rb') as photo:
            bot.send_photo(message.chat.id, photo)
    except:
        pass

    text = format_text("""
    🤖 Школьный помощник

    Версия: 3.0
    Используемые технологии:
    - OpenAI API
    - Kandinsky 3.1
    - Python 3.10
    """)

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=create_main_menu(),
        parse_mode='HTML'
    )


@bot.message_handler(func=lambda m: m.text == '📝 Тест')
def start_quiz(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [types.KeyboardButton(f'{i} класс') for i in range(1, 12)]
    markup.add(*buttons)
    markup = add_back_button(markup)

    bot.send_message(
        message.chat.id,
        "Выбери свой класс:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: re.match(r'^\d+ класс$', m.text))
def handle_grade(message):
    grade = int(message.text.split()[0])
    if grade not in GRADE_SUBJECTS:
        bot.send_message(message.chat.id, "❌ Недопустимый класс")
        return send_welcome(message)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(subject) for subject in GRADE_SUBJECTS[grade]]
    markup.add(*buttons)
    markup = add_back_button(markup)

    bot.send_message(
        message.chat.id,
        f"Выбери предмет для теста ({grade} класс):",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, handle_subject, grade)


def handle_subject(message, grade):
    if message.text == '🔙 На главную':
        return send_welcome(message)

    subject = message.text
    if subject not in GRADE_SUBJECTS[grade]:
        bot.send_message(message.chat.id, "❌ Недопустимый предмет для выбранного класса")
        return start_quiz(message)

    bot.send_message(message.chat.id, "🔄 Генерирую вопрос...")

    question_data = generate_ai_question(grade, subject)
    if not question_data:
        bot.send_message(message.chat.id, "❌ Не удалось сгенерировать вопрос. Попробуй позже.")
        return send_welcome(message)

    parts = question_data.split('_')
    question = parts[0]
    answers = parts[1:5]
    correct_num = int(parts[5]) - 1

    bot.register_next_step_handler(
        message,
        check_answer,
        correct=answers[correct_num],
        subject=subject,
        grade=grade
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for ans in answers:
        markup.add(types.KeyboardButton(ans))
    markup = add_back_button(markup)

    bot.send_message(
        message.chat.id,
        f"❓ Вопрос ({subject}, {grade} класс):\n\n{question}",
        reply_markup=markup
    )


def check_answer(message, correct, subject, grade):
    if message.text == '🔙 На главную':
        return send_welcome(message)

    if message.text == correct:
        reply = "✅ Правильно! Молодец!"
    else:
        reply = f"❌ Неверно! Правильный ответ: {correct}"

    bot.send_message(message.chat.id, reply)

    recommendations = generate_recommendations(subject)
    rec1, rec2 = recommendations.split('_')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(rec1))
    markup.add(types.KeyboardButton(rec2))
    markup.add(types.KeyboardButton('🔙 На главную'))

    bot.send_message(
        message.chat.id,
        "📚 Возможно вы хотите узнать об этом:",
        reply_markup=markup
    )

    bot.register_next_step_handler(
        message,
        handle_recommendation,
        subject=subject,
        grade=grade,
        prev_recommendations=[rec1, rec2]
    )


def handle_recommendation(message, subject, grade, prev_recommendations=None):
    if prev_recommendations is None:
        prev_recommendations = []

    if message.text == '🔙 На главную':
        return send_welcome(message)

    if message.text in prev_recommendations:
        # Если выбрана одна из предыдущих рекомендаций, просто объясняем ее
        topic = message.text
    else:
        # Иначе генерируем новые рекомендации на основе выбора пользователя
        topic = message.text
        recommendations = generate_recommendations(topic)
        rec1, rec2 = recommendations.split('_')
        prev_recommendations = [rec1, rec2]

    bot.send_message(message.chat.id, f"🔄 Готовлю информацию по теме: {topic}...")

    try:
        response = ai_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{
                "role": "system",
                "content": "Ты - учитель для школьников. Объясняй просто и понятно, с примерами."
            }, {
                "role": "user",
                "content": f"Объясни тему '{topic}' для школьника {grade} класса"
            }],
            temperature=0.7,
            max_tokens=1500
        )

        explanation = format_text(response.choices[0].message.content)

        if len(explanation) > 4000:
            for x in range(0, len(explanation), 4000):
                bot.send_message(message.chat.id, explanation[x:x + 4000], parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, explanation, parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    # После объяснения снова предлагаем рекомендации
    recommendations = generate_recommendations(topic)
    rec1, rec2 = recommendations.split('_')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(rec1))
    markup.add(types.KeyboardButton(rec2))
    markup.add(types.KeyboardButton('🔙 На главную'))

    bot.send_message(
        message.chat.id,
        "📚 Возможно вы хотите узнать об этом:",
        reply_markup=markup
    )

    # Регистрируем следующий шаг с обновленными рекомендациями
    bot.register_next_step_handler(
        message,
        handle_recommendation,
        subject=subject,
        grade=grade,
        prev_recommendations=[rec1, rec2]
    )


@bot.message_handler(func=lambda m: m.text == '📚 Объяснить тему')
def request_topic(message):
    bot.send_message(
        message.chat.id,
        "📝 Напиши, какую тему объяснить (например: 'дроби', 'проценты', 'падежи'):",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('🔙 На главную')
    )
    bot.register_next_step_handler(message, explain_topic)


def explain_topic(message):
    if message.text == '🔙 На главную':
        return send_welcome(message)

    topic = message.text
    bot.send_message(message.chat.id, f"🔄 Ищу информацию по теме '{topic}'...")

    try:
        response = ai_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{
                "role": "system",
                "content": "Ты - учитель для школьников. Объясняй просто и понятно, с примерами."
            }, {
                "role": "user",
                "content": f"Объясни тему '{topic}' для школьника"
            }],
            temperature=0.7,
            max_tokens=1500
        )

        explanation = format_text(response.choices[0].message.content)

        if len(explanation) > 4000:
            for x in range(0, len(explanation), 4000):
                bot.send_message(message.chat.id, explanation[x:x + 4000], parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, explanation, parse_mode='HTML')

        recommendations = generate_recommendations(topic)
        rec1, rec2 = recommendations.split('_')

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(rec1))
        markup.add(types.KeyboardButton(rec2))
        markup.add(types.KeyboardButton('🔙 На главную'))

        bot.send_message(
            message.chat.id,
            "📚 Возможно вы хотите узнать об этом:",
            reply_markup=markup
        )

        bot.register_next_step_handler(
            message,
            handle_recommendation,
            subject=topic,
            grade=5,
            prev_recommendations=[rec1, rec2]
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
        send_welcome(message)


@bot.message_handler(func=lambda m: m.text == '🎨 Генерация изображений')
def start_image_generation(message):
    if not fusion_api:
        bot.send_message(message.chat.id, "❌ Сервис генерации изображений временно недоступен")
        return send_welcome(message)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton('🖼️ Обычное изображение'),
        types.KeyboardButton('✏️ Контурный рисунок'),
        types.KeyboardButton('🌈 Выбрать стиль')
    ]
    markup.add(*buttons)
    markup = add_back_button(markup)

    bot.send_message(
        message.chat.id,
        "🎨 Генерация изображений:\n\nВыбери тип изображения:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == '🌈 Выбрать стиль')
def choose_style(message):
    if not fusion_api:
        bot.send_message(message.chat.id, "❌ Сервис генерации изображений временно недоступен")
        return send_welcome(message)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(style) for style in fusion_api.STYLES[:10]]
    markup.add(*buttons)
    markup = add_back_button(markup)

    bot.send_message(
        message.chat.id,
        "🖼 Выбери стиль для генерации:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_style_selection)


def process_style_selection(message):
    if message.text == '🔙 На главную':
        return send_welcome(message)

    if not fusion_api or message.text not in fusion_api.STYLES:
        bot.send_message(message.chat.id, "❌ Выбран недопустимый стиль")
        return start_image_generation(message)

    if not hasattr(bot, 'session_data'):
        bot.session_data = {}

    bot.session_data[message.chat.id] = {'style': message.text}
    bot.send_message(
        message.chat.id,
        f"✅ Выбран стиль: {message.text}\n\nТеперь опиши изображение, которое нужно сгенерировать:",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('🔙 На главную')
    )
    bot.register_next_step_handler(message, process_image_generation)


@bot.message_handler(func=lambda m: m.text in ['🖼️ Обычное изображение', '✏️ Контурный рисунок'])
def handle_image_type(message):
    if not fusion_api:
        bot.send_message(message.chat.id, "❌ Сервис генерации изображений временно недоступен")
        return send_welcome(message)

    image_type = 'standard' if message.text == '🖼️ Обычное изображение' else 'contour'

    if not hasattr(bot, 'session_data'):
        bot.session_data = {}

    bot.session_data[message.chat.id] = {'image_type': image_type}

    if image_type == 'contour':
        bot.session_data[message.chat.id]['style'] = 'DEFAULT'
        bot.session_data[message.chat.id]['negative_prompt'] = "цвета, заливка, тени, градиенты"

    bot.send_message(
        message.chat.id,
        "✏️ Опиши изображение, которое нужно сгенерировать:",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('🔙 На главную')
    )
    bot.register_next_step_handler(message, process_image_generation)


def process_image_generation(message):
    if message.text == '🔙 На главную':
        return send_welcome(message)

    if not fusion_api:
        bot.send_message(message.chat.id, "❌ Сервис генерации изображений временно недоступен")
        return send_welcome(message)

    if not hasattr(bot, 'session_data') or message.chat.id not in bot.session_data:
        bot.session_data = {message.chat.id: {}}

    chat_data = bot.session_data.get(message.chat.id, {})
    prompt = message.text
    style = chat_data.get('style', 'DEFAULT')
    negative_prompt = chat_data.get('negative_prompt', None)

    if chat_data.get('image_type') == 'contour':
        prompt = f"контурный рисунок {prompt}, черно-белый, без заливки, только линии, с низкой детализацией, МАКСИМАЛЬНО светлый рисунок, без заливки-"

    bot.send_message(message.chat.id, "🔄 Генерирую изображение... Это может занять до 2 минут.")

    try:
        uuid = fusion_api.generate(
            prompt=prompt,
            style=style,
            negative_prompt=negative_prompt
        )

        if not uuid:
            raise Exception("Не удалось начать генерацию")

        image_data = fusion_api.check_generation_status(uuid)

        if not image_data:
            raise Exception("Генерация не завершена или произошла ошибка")

        image_bytes = base64.b64decode(image_data)
        img = Image.open(BytesIO(image_bytes))

        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        bot.send_photo(message.chat.id, img_byte_arr)
        bot.send_message(
            message.chat.id,
            "✅ Изображение готово!",
            reply_markup=create_main_menu())
        bot.send_message(
            message.chat.id,
            "✅ Совет. Возьми устройство с большим экраном и подложи его под лист бумаги. Далее просто проводи контур по контурам,которые просвечивают",
            reply_markup=create_main_menu()
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка при генерации изображения: {str(e)}",
            reply_markup=create_main_menu()
        )

    if message.chat.id in bot.session_data:
        del bot.session_data[message.chat.id]


@bot.message_handler(func=lambda m: m.text == '🧮 Калькулятор')
def calculator(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    buttons = [
        types.KeyboardButton('7'), types.KeyboardButton('8'), types.KeyboardButton('9'), types.KeyboardButton('/'),
        types.KeyboardButton('4'), types.KeyboardButton('5'), types.KeyboardButton('6'), types.KeyboardButton('*'),
        types.KeyboardButton('1'), types.KeyboardButton('2'), types.KeyboardButton('3'), types.KeyboardButton('-'),
        types.KeyboardButton('0'), types.KeyboardButton('.'), types.KeyboardButton('='), types.KeyboardButton('+'),
        types.KeyboardButton('C'), types.KeyboardButton('🚪 Выход'),
        types.KeyboardButton('🔙 На главную')
    ]
    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        "🧮 Калькулятор\n\nТекущее выражение: \n(пусто)",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_calculation, current_expression="")


def process_calculation(message, current_expression):
    if message.text in ['🔙 На главную', '🚪 Выход']:
        return send_welcome(message)

    if message.text == 'C':
        current_expression = ""
    elif message.text == '=':
        try:
            if not re.match(r'^[\d+\-*/.() ]+$', current_expression):
                raise ValueError("Недопустимые символы в выражении")

            result = eval(current_expression)
            current_expression = str(result)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
            return calculator(message)
    else:
        current_expression += message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    buttons = [
        types.KeyboardButton('7'), types.KeyboardButton('8'), types.KeyboardButton('9'), types.KeyboardButton('/'),
        types.KeyboardButton('4'), types.KeyboardButton('5'), types.KeyboardButton('6'), types.KeyboardButton('*'),
        types.KeyboardButton('1'), types.KeyboardButton('2'), types.KeyboardButton('3'), types.KeyboardButton('-'),
        types.KeyboardButton('0'), types.KeyboardButton('.'), types.KeyboardButton('='), types.KeyboardButton('+'),
        types.KeyboardButton('C'), types.KeyboardButton('🚪 Выход'),
        types.KeyboardButton('🔙 На главную')
    ]
    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        f"🧮 Калькулятор\n\nТекущее выражение: {current_expression}",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_calculation, current_expression=current_expression)
    return None


@bot.message_handler(func=lambda m: m.text == '🔙 На главную')
def back_to_main(message):
    send_welcome(message)


@bot.message_handler(func=lambda m: True)
def handle_other_messages(message):
    bot.send_message(
        message.chat.id,
        "Я не понял ваш запрос. Пожалуйста, используйте кнопки меню.",
        reply_markup=create_main_menu()
    )


if not hasattr(bot, 'session_data'):
    bot.session_data = {}

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()