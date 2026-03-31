import telebot
from telebot import types
import database
import uuid
from datetime import datetime, timedelta
import os
import plantnet_api
import tempfile
import llm_support

database.init_db()

bot = telebot.TeleBot('8646889259:AAEmBd4FjbkjhXj4TBwOdV97Tvzpq_owgfw')

temp_plants = {}
user_states = {}

if not os.path.exists('temp_photos'):
    os.makedirs('temp_photos')


def truncate_name(name, max_length=20):
    if len(name) <= max_length:
        return name
    return name[:max_length - 1] + "…"


@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    database.register_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('🌿 Мои растения')
    btn2 = types.KeyboardButton('👀 Распознать растение')
    btn3 = types.KeyboardButton('💡 Совет дня')
    btn4 = types.KeyboardButton('❓ Задать вопрос')
    markup.add(btn1, btn2, btn3, btn4)

    plant_count = database.get_plant_count(message.from_user.id)

    tip = llm_support.llm.generate_daily_tip()
    welcome_text = (f"🪷🌸  Добро пожаловать в ваш сад!  🌸🪷\n\n"
                    f"Растений в саду: {plant_count}\n\n"
                    f"{tip}")

    bot.send_message(message.from_user.id, welcome_text, reply_markup=markup, parse_mode='Markdown')


@bot.message_handler(commands=['tip'])
def daily_tip(message):
    bot.send_message(message.chat.id, "💭 Генерирую совет дня...")
    tip = llm_support.llm.generate_daily_tip()
    bot.send_message(message.chat.id, tip, parse_mode='Markdown')


@bot.message_handler(commands=['fact'])
def plant_fact(message):
    """Команда для получения факта о растении"""
    plants = database.get_user_plants(message.from_user.id)

    if plants:
        import random
        plant = random.choice(plants)
        plant_name = plant[0]

        bot.send_message(message.chat.id, f"🔍 Ищу интересный факт о {plant_name}...")
        fact = llm_support.llm.get_plant_fact(plant_name)
        bot.send_message(message.chat.id, fact, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "🔍 Ищу интересный факт о растениях...")
        fact = llm_support.llm.get_plant_fact("растениях")
        bot.send_message(message.chat.id, fact, parse_mode='Markdown')


@bot.message_handler(commands=['ask'])
def ask_question(message):
    """Команда для вопроса"""
    question = message.text.replace('/ask', '').strip()
    if question:
        process_question(message, question)
    else:
        msg = bot.send_message(message.chat.id, "❓ Задайте ваш вопрос о растениях:")
        bot.register_next_step_handler(msg, process_question)


def process_question(message, question=None):
    """Обрабатывает вопрос пользователя"""
    if not question:
        question = message.text

    user_plants = database.get_user_plants(message.from_user.id)

    bot.send_message(message.chat.id, "🌿 Думаю над ответом...")
    answer = llm_support.llm.answer_question(question, user_plants)
    bot.send_message(message.chat.id, answer, parse_mode='Markdown')


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    user_id = message.from_user.id

    if user_id in user_states and user_states[user_id].get('waiting_for_name'):
        plant_id = user_states[user_id]['plant_id']
        plant_data = temp_plants.get(plant_id)

        if plant_data:
            custom_name = message.text.strip()
            plant_data['custom_name'] = custom_name
            save_plant_to_garden(user_id, plant_id, plant_data)
        else:
            bot.send_message(user_id, "❌ Данные о растении устарели. Попробуйте распознать заново.")
            del user_states[user_id]
        return

    if user_id in user_states and user_states[user_id].get('waiting_for_question'):
        question = message.text.strip()
        del user_states[user_id]
        process_question(message, question)
        return

    if message.text == '🌿 Мои растения':
        plants = database.get_user_plants(message.from_user.id)

        if not plants:
            bot.send_message(
                message.from_user.id,
                '🌱 Ваш сад пока пуст. Загрузите фото растения, чтобы добавить его!',
                parse_mode='Markdown'
            )
            return

        markup = types.InlineKeyboardMarkup(row_width=1)

        for i, plant in enumerate(plants, 1):
            plant_name = plant[0]
            truncated_name = truncate_name(plant_name, 15)
            button = types.InlineKeyboardButton(
                f"{truncated_name}",
                callback_data=f"plant_{i - 1}"
            )
            markup.add(button)

        clear_button = types.InlineKeyboardButton("🗑 Очистить весь сад", callback_data="clear_garden")
        markup.add(clear_button)

        temp_plants[f"user_{message.from_user.id}_plants"] = plants

        bot.send_message(
            message.from_user.id,
            "🪴  *Твои растения*  🪴",
            parse_mode='Markdown',
            reply_markup=markup
        )

    elif message.text == '👀 Распознать растение':
        bot.send_message(
            message.from_user.id,
            '🧐 Пришлите мне изображение с растением, и я расскажу вам о нём',
            parse_mode='Markdown'
        )

    elif message.text == '💡 Совет дня':
        bot.send_message(message.chat.id, "💭 Генерирую совет дня...")
        tip = llm_support.llm.generate_daily_tip()
        bot.send_message(message.chat.id, tip, parse_mode='Markdown')

    elif message.text == '❓ Задать вопрос':
        msg = bot.send_message(
            message.from_user.id,
            "❓ Задайте ваш вопрос о растениях. Я постараюсь помочь!\n\n"
            "Например:\n"
            "- Как часто поливать кактус?\n"
            "- Почему желтеют листья?\n"
            "- Какое освещение нужно фикусу?"
        )
        user_states[user_id] = {'waiting_for_question': True}

    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('🌿 Мои растения')
        btn2 = types.KeyboardButton('👀 Распознать растение')
        btn3 = types.KeyboardButton('💡 Совет дня')
        btn4 = types.KeyboardButton('❓ Задать вопрос')
        markup.add(btn1, btn2, btn3, btn4)

        help_text = (
            "🌱 *Я бот для ухода за растениями!* 🌱\n\n"
            "Я не понимаю обычные сообщения. Пожалуйста, используйте кнопки меню или команды:\n\n"
            "📱 *Кнопки меню:*\n"
            "• 🌿 Мои растения - посмотреть ваш сад\n"
            "• 👀 Распознать растение - определить растение по фото\n"
            "• 💡 Совет дня - полезный совет по уходу\n"
            "• ❓ Задать вопрос - спросить о растениях\n\n"
            "⌨️ *Команды:*\n"
            "• /start - начать заново\n"
            "• /tip - совет дня\n"
            "• /fact - интересный факт о растении\n"
            "• /ask [вопрос] - задать вопрос\n\n"
            "📸 *Или просто отправьте фото растения, и я его распознаю!*"
        )

        bot.send_message(
            message.from_user.id,
            help_text,
            parse_mode='Markdown',
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith('add_'))
def start_adding_process(call):
    plant_id = call.data.replace('add_', '')
    plant_data = temp_plants.get(plant_id)

    if not plant_data:
        bot.answer_callback_query(call.id, "❌ Данные о растении устарели. Попробуйте распознать заново.")
        return

    bot.answer_callback_query(call.id)

    ask_for_plant_name(call.from_user.id, plant_id)


def save_plant_to_garden(user_id, plant_id, plant_data):
    """Сохраняет растение в базу данных"""

    base_name = plant_data['plant_name']
    custom_name = plant_data.get('custom_name')

    if custom_name:
        final_name = f"{base_name} {custom_name}"
    else:
        existing_count = get_next_plant_number(user_id, base_name)
        if existing_count == 1:
            final_name = base_name
        else:
            final_name = f"{base_name} {existing_count}"

    watering_info = f"{plant_data['watering_amount']}, {plant_data['watering_frequency']}"
    photo_file_id = plant_data.get('photo_file_id')

    success = database.add_plant_to_garden(
        user_id=user_id,
        plant_name=final_name,
        watering=watering_info,
        lighting=plant_data['lighting'],
        photo_file_id=photo_file_id
    )

    if success:
        del temp_plants[plant_id]
        if user_id in user_states:
            del user_states[user_id]
        bot.send_message(user_id, f"✅ *{final_name}* добавлен в ваш сад!", parse_mode='Markdown')
    else:
        bot.send_message(user_id, "❌ Ошибка при добавлении растения")
        print(f"🔴 Ошибка при добавлении растения {final_name} в БД")


@bot.callback_query_handler(func=lambda call: call.data.startswith('plant_'))
def show_plant_details(call):
    """Показывает детали выбранного растения"""
    plant_index = int(call.data.replace('plant_', ''))

    plants_key = f"user_{call.from_user.id}_plants"
    plants = temp_plants.get(plants_key)

    if not plants or plant_index >= len(plants):
        bot.answer_callback_query(call.id, "❌ Данные устарели. Нажмите 'Мои растения' заново.")
        return

    plant = plants[plant_index]
    plant_name, watering, lighting, added_at, photo_file_id = plant

    try:
        added_date = datetime.strptime(added_at, '%Y-%m-%d %H:%M:%S')
        formatted_added_date = added_date.strftime('%d %B %Y')
        months = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }
        for eng, rus in months.items():
            formatted_added_date = formatted_added_date.replace(eng, rus)
    except:
        formatted_added_date = added_at[:10]

    details = (
        f"✨ *{plant_name}* ✨\n\n"
        f"*Полив:*\n"
        f"    - {watering}\n\n"
        f"*Освещение:*\n"
        f"    - {lighting}\n\n"
        f"*Добавлен:* {formatted_added_date}"
    )

    markup = types.InlineKeyboardMarkup()
    delete_button = types.InlineKeyboardButton(
        "❌ Удалить из сада",
        callback_data=f"delete_{plant_index}"
    )
    markup.add(delete_button)

    bot.answer_callback_query(call.id)

    bot.send_photo(
        call.message.chat.id,
        photo_file_id,
        caption=details,
        parse_mode='Markdown',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_plant(call):
    """Удаляет растение из сада"""
    plant_index = int(call.data.replace('delete_', ''))

    plants_key = f"user_{call.from_user.id}_plants"
    plants = temp_plants.get(plants_key)

    if not plants or plant_index >= len(plants):
        bot.answer_callback_query(call.id, "❌ Данные устарели. Нажмите 'Мои растения' заново.")
        return

    plant = plants[plant_index]
    plant_name = plant[0]

    success = database.delete_plant(call.from_user.id, plant_name)

    if success:
        bot.answer_callback_query(call.id, f"✅ {plant_name} удалён из вашего сада!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

        plants.pop(plant_index)
        if plants:
            temp_plants[plants_key] = plants
        else:
            temp_plants.pop(plants_key, None)

        bot.send_message(
            call.message.chat.id,
            f"🌱 Растение '{plant_name}' удалено."
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка при удалении растения")


@bot.callback_query_handler(func=lambda call: call.data == "clear_garden")
def clear_garden(call):
    """Очищает весь сад пользователя"""
    success = database.clear_user_garden(call.from_user.id)

    if success:
        bot.answer_callback_query(call.id, "🗑 Весь сад очищен!")

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )

        plants_key = f"user_{call.from_user.id}_plants"
        temp_plants.pop(plants_key, None)

        bot.send_message(
            call.message.chat.id,
            "🌱 Ваш сад успешно очищен. Теперь можно добавить новые растения!"
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка при очистке сада")


@bot.callback_query_handler(func=lambda call: call.data.startswith('no_name_'))
def save_without_name(call):
    """Сохраняет растение без имени"""
    plant_id = call.data.replace('no_name_', '')
    plant_data = temp_plants.get(plant_id)

    if not plant_data:
        bot.answer_callback_query(call.id, "❌ Данные о растении устарели. Попробуйте распознать заново.")
        return

    bot.delete_message(call.message.chat.id, call.message.message_id)

    plant_data['custom_name'] = None

    if call.from_user.id in user_states:
        del user_states[call.from_user.id]

    save_plant_to_garden(call.from_user.id, plant_id, plant_data)
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    photo = message.photo[-1]
    file_id = photo.file_id

    processing_msg = bot.send_message(
        message.chat.id,
        "🔍 Распознаю растение... Подождите немного"
    )

    temp_dir = tempfile.gettempdir()
    temp_image_path = os.path.join(temp_dir, f"plant_{message.from_user.id}_{datetime.now().timestamp()}.jpg")

    try:
        if not plantnet_api.download_image_from_telegram(bot, file_id, temp_image_path):
            bot.edit_message_text(
                "❌ Не удалось загрузить изображение. Попробуйте ещё раз.",
                chat_id=message.chat.id,
                message_id=processing_msg.message_id
            )
            return

        api = plantnet_api.PlantNetAPI()

        result = api.identify_plant(temp_image_path)

        if not result:
            bot.edit_message_text(
                "❌ Не удалось распознать растение. Попробуйте другое изображение.",
                chat_id=message.chat.id,
                message_id=processing_msg.message_id
            )
            return

        best_match = api.get_best_match(result)
        if best_match and best_match.score < 0.1:
            bot.edit_message_text(
                "⚠️ Низкая достоверность определения. Попробуйте сфотографировать растение более четко.\n\n"
                "Советы для лучшего распознавания:\n"
                "📸 Фотографируйте цветы, листья или плоды\n"
                "🌿 Делайте фото при хорошем освещении\n"
                "🎯 Старайтесь сфокусироваться на деталях",
                chat_id=message.chat.id,
                message_id=processing_msg.message_id
            )
            return

        bot.edit_message_text(
            "🌿 Получаю информацию об уходе...",
            chat_id=message.chat.id,
            message_id=processing_msg.message_id
        )

        care_info = llm_support.llm.get_plant_care_info(
            best_match.scientific_name,
            best_match.common_names
        )

        plant_name = best_match.scientific_name
        if best_match.common_names:
            common_names_str = ', '.join(best_match.common_names[:3])
        else:
            common_names_str = "нет данных"

        score_percent = best_match.score * 100
        organ_info = api.get_predicted_organ(result)
        organ_text = f"\n\n🔍 Распознано по: {organ_info}" if organ_info else ""

        care_text = ""
        if care_info:
            care_text = f"""
\n*Весна-лето:*
- Освещение: {care_info['spring_summer']['lighting']}
- Полив: {care_info['spring_summer']['watering']}, {care_info['spring_summer']['watering_frequency']}
- Температура: {care_info['spring_summer']['temperature']}

*Осень-зима:*
- Освещение: {care_info['fall_winter']['lighting']}
- Полив: {care_info['fall_winter']['watering']}, {care_info['fall_winter']['watering_frequency']}
- Температура: {care_info['fall_winter']['temperature']}

*Особенность растения:* {care_info['feature']}"""
        else:
            care_text = """Что-то пошло не так :("""

        final_text = (
            f"🌱 *Распознано растение:* {plant_name}\n\n"
            f"*Названия:* {common_names_str}\n"
            f"*Семейство:* {best_match.family}\n"
            f"*Род:* {best_match.genus}\n"
            f"*Достоверность:* {score_percent:.2f}%{organ_text}\n"
            f"{care_text}"
        )

        plant_id = str(uuid.uuid4())

        watering_recommendation = "ошибка"
        watering_frequency = "ошибка"
        if care_info:
            watering_recommendation = care_info['spring_summer']['watering']
            watering_frequency = care_info['spring_summer']['watering_frequency']

        lighting_recommendation = "ошибка"
        if care_info:
            lighting_recommendation = care_info['spring_summer']['lighting']

        temp_plants[plant_id] = {
            'user_id': message.from_user.id,
            'plant_name': best_match.scientific_name,
            'watering_amount': watering_recommendation,
            'watering_frequency': watering_frequency,
            'lighting': lighting_recommendation,
            'photo_file_id': file_id,
            'common_names': best_match.common_names,
            'family': best_match.family,
            'genus': best_match.genus,
            'score': best_match.score,
            'care': care_text
        }

        markup = types.InlineKeyboardMarkup()
        add_button = types.InlineKeyboardButton(
            "➕ Добавить в мой сад",
            callback_data=f"add_{plant_id}"
        )
        markup.add(add_button)

        bot.delete_message(message.chat.id, processing_msg.message_id)

        bot.send_message(
            message.chat.id,
            final_text,
            parse_mode='Markdown',
            reply_markup=markup
        )

        if api.remaining_requests is not None:
            print(f"Осталось запросов на сегодня: {api.remaining_requests}")

    except Exception as e:
        bot.edit_message_text(
            "❌ Извините, произошла ошибка при распознавании. Попробуйте ещё раз.",
            chat_id=message.chat.id,
            message_id=processing_msg.message_id
        )
        print(f"Error in handle_photo: {e}")

    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)


@bot.message_handler(commands=['help'])
def help_command(message):
    """Показывает список доступных команд"""
    help_text = (
        "🌱 *Доступные команды и действия* 🌱\n\n"
        "📱 *Кнопки меню:*\n"
        "• 🌿 Мои растения - посмотреть все растения в вашем саду\n"
        "• 👀 Распознать растение - отправить фото для определения\n"
        "• 💡 Совет дня - получить полезный совет по уходу\n"
        "• ❓ Задать вопрос - задать вопрос о растениях\n\n"
        "⌨️ *Команды:*\n"
        "• /start - перезапустить бота\n"
        "• /help - показать это сообщение\n"
        "• /tip - получить совет дня\n"
        "• /fact - получить интересный факт о растении\n"
        "• /ask [вопрос] - задать вопрос (например: /ask как поливать кактус)\n\n"
        "📸 *Распознавание:*\n"
        "Просто отправьте фото растения, и я определю его!\n\n"
        "❓ *Вопросы:*\n"
        "Вы можете спросить меня о поливе, освещении, болезнях растений и многом другом!"
    )

    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode='Markdown'
    )


def ask_for_plant_name(user_id, plant_id):
    markup = types.InlineKeyboardMarkup()
    no_button = types.InlineKeyboardButton("Нет", callback_data=f"no_name_{plant_id}")
    markup.add(no_button)

    bot.send_message(
        user_id,
        "Не хотите ли дать ему имя?😚",
        reply_markup=markup
    )

    user_states[user_id] = {
        'waiting_for_name': True,
        'plant_id': plant_id
    }


def get_next_plant_number(user_id, base_name):
    plants = database.get_user_plants(user_id)
    count = 0
    for plant in plants:
        plant_name = plant[0]
        if plant_name == base_name:
            count += 1
        elif plant_name.startswith(base_name + ' ') and plant_name[len(base_name) + 1:].isdigit():
            count += 1
    return count + 1


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True, interval=0)