import os
import time
import random
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()


class LLMService:
    """Сервис для работы с LLM (Cerebras)"""

    def __init__(self, provider: str = "cerebras"):
        self.provider = provider
        self.last_request_time = 0
        self.min_request_interval = 1

        self.api_key = "csk-jv6xvvfd92x4n5cen8rxehr3fnehpkeept5r84d9etnf8vvw"

        self.model_name = "llama3.1-8b"

        if provider == "cerebras":
            try:
                if self.api_key:
                    self.client = Cerebras(api_key=self.api_key)
                    print(f"✅ Cerebras инициализирован с моделью: {self.model_name}")
                else:
                    print("⚠️ API ключ не найден")
                    self.client = None
            except Exception as e:
                print(f"⚠️ Ошибка инициализации Cerebras: {e}")
                self.client = None
        else:
            self.client = None

    def _rate_limit(self):
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            time.sleep(self.min_request_interval - (current_time - self.last_request_time))
        self.last_request_time = time.time()

    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        """Генерация текста через Cerebras"""
        self._rate_limit()

        if self.provider == "cerebras":
            return self._generate_cerebras(prompt, max_tokens)
        return None

    def _generate_cerebras(self, prompt: str, max_tokens: int) -> str:
        if not self.client:
            print("Cerebras not available, using fallback")
            return None

        try:
            messages = [
                {"role": "user", "content": prompt}
            ]

            completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                max_completion_tokens=max_tokens,
                temperature=0.7,
                top_p=0.95,
                stream=False
            )

            if completion and completion.choices and completion.choices[0].message:
                return completion.choices[0].message.content.strip()
            else:
                print(f"Cerebras error: Empty response")
                return None

        except Exception as e:
            print(f"Cerebras error: {e}")
            return None

    def get_plant_care_info(self, plant_name: str, common_names: list = None) -> dict:
        """Получает информацию об уходе за растением от LLM"""
        if not self._is_available():
            return None

        names_str = plant_name
        if common_names and len(common_names) > 0:
            names_str = f"{plant_name} (также известное как {', '.join(common_names[:3])})"

        prompt = f"""
        Ты - эксперт по комнатным растениям. Предоставь информацию об уходе за растением {names_str}.

        Ответь в следующем формате (используй только русский язык):

        Весна-лето:
        - Освещение: [тип освещения]
        - Полив: [частота полива], [количество раз в неделю/месяц]
        - Температура: [диапазон температур]

        Осень-зима:
        - Освещение: [тип освещения]
        - Полив: [частота полива], [количество раз в неделю/месяц]
        - Температура: [диапазон температур]

        Особенность растения: [одно-два предложения об особенностях: ядовитость, аромат, очищение воздуха, интересные факты]

        Если растение не является комнатным, укажи это и дай общие рекомендации.
        """

        response = self.generate(prompt, max_tokens=500)

        if response:
            return self._parse_care_info(response)
        return None

    def _parse_care_info(self, text: str) -> dict:
        """Парсит информацию об уходе из текста"""
        care_info = {
            'spring_summer': {
                'lighting': 'ошибка',
                'watering': 'ошибка',
                'watering_frequency': 'ошибка',
                'temperature': 'ошибка'
            },
            'fall_winter': {
                'lighting': 'ошибка',
                'watering': 'ошибка',
                'watering_frequency': 'ошибка',
                'temperature': 'ошибка'
            },
            'feature': 'Нет дополнительной информации'
        }

        try:
            lines = text.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if 'Весна-лето' in line or 'Весна' in line:
                    current_section = 'spring_summer'
                elif 'Осень-зима' in line or 'Осень' in line:
                    current_section = 'fall_winter'
                elif 'Особенность' in line or 'особенность' in line:
                    if ':' in line:
                        feature = line.split(':', 1)[1].strip()
                        if feature:
                            care_info['feature'] = feature
                    current_section = None
                elif current_section and '-' in line and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower().replace(':', '').strip('-')
                        value = parts[1].strip()

                        if 'освещение' in key:
                            care_info[current_section]['lighting'] = value if value else 'ошибка'
                        elif 'полив' in key:
                            if ',' in value:
                                water_parts = value.split(',', 1)
                                care_info[current_section]['watering'] = water_parts[0].strip()
                                if len(water_parts) > 1:
                                    care_info[current_section]['watering_frequency'] = water_parts[1].strip()
                            else:
                                # Если нет запятой, пробуем найти слово "раз" в строке
                                if 'раз' in value:
                                    care_info[current_section]['watering'] = value
                                else:
                                    care_info[current_section]['watering'] = value
                                    care_info[current_section]['watering_frequency'] = 'по необходимости'
                        elif 'температура' in key:
                            care_info[current_section]['temperature'] = value if value else 'ошибка'
        except Exception as e:
            print(f"Ошибка при парсинге информации об уходе: {e}")

        return care_info

    def is_gardening_related(self, question: str) -> bool:
        return True

    def get_plant_fact(self, plant_name: str) -> str:
        """Генерирует интересный факт о растении"""

        if self._is_available():
            prompt = f"""
            Расскажи один короткий интересный факт о растении {plant_name}.
            Максимум 2 предложения. Используй эмодзи 🌱💚🌿.
            """
            response = self.generate(prompt, max_tokens=2000)
            return response

    def generate_daily_tip(self) -> str:
        """Генерирует совет дня"""

        if self._is_available():
            prompt = """
            Придумай короткий полезный совет по уходу за комнатными растениями.
            Начни с эмодзи 💡. Максимум 1 предложения.
            """
            response = self.generate(prompt, max_tokens=2000)

            return response

    def answer_question(self, question: str, user_plants: list = None) -> str:
        """Отвечает на вопрос пользователя о растениях"""

        if not self._is_available():
            return ("❌ Модель недоступна. Спросите позже")

        prompt = f"""
        Ты - помощник по уходу за растениями. Отвечай кратко и по существу. Используй эмодзи только если уместно
        Если вопрос не связан с садоводством или растениями то ответь следующее:
        '💔 Кажется, что [вставь тему вопроса] не [связана, связаны, связано и связан] с садоводством. Попробуйте спросить по-другому.'

        Вопрос: {question}
        """

        response = self.generate(prompt, max_tokens=2000)

        return response

    def _is_available(self) -> bool:
        """Проверяет, доступна ли нейросеть"""
        if self.provider == "cerebras":
            return bool(self.client)
        return False


llm = LLMService(provider='cerebras')