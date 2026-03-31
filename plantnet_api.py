import requests
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import os

API_KEY = "2b1090b5P8SCtE4dF3MEm5i"
BASE_URL = "https://my-api.plantnet.org/v2"
PROJECT = "all"


@dataclass
class PlantIdentification:
    scientific_name: str
    common_names: List[str]
    genus: str
    family: str
    score: float
    species: str


class PlantNetAPI:
    def __init__(self, api_key: str = API_KEY, project: str = PROJECT):
        self.api_key = api_key
        self.project = project
        self.remaining_requests = None

    def identify_plant(self, image_path: str, organ: str = 'auto') -> Optional[Dict]:
        if not image_path:
            print("Ошибка: не указан путь к изображению")
            return None

        api_endpoint = f"{BASE_URL}/identify/{self.project}?api-key={self.api_key}"

        try:
            with open(image_path, 'rb') as image_file:
                files = [('images', (image_path, image_file, 'image/jpeg'))]
                data = {'organs': [organ]}

                response = requests.post(api_endpoint, files=files, data=data)

                if response.status_code == 200:
                    result = response.json()
                    self.remaining_requests = result.get('remainingIdentificationRequests')
                    return result
                else:
                    print(f"Ошибка API: {response.status_code}")
                    print(f"Ответ: {response.text}")
                    return None

        except Exception as e:
            print(f"Ошибка при запросе к API: {e}")
            return None

    def parse_identification_result(self, result: Dict) -> List[PlantIdentification]:
        if not result or 'results' not in result:
            return []

        plants = []
        for item in result['results']:
            species_data = item['species']

            scientific_name = species_data.get('scientificNameWithoutAuthor', '')
            scientific_name_full = species_data.get('scientificName', scientific_name)
            common_names = species_data.get('commonNames', [])

            genus_data = species_data.get('genus', {})
            genus = genus_data.get('scientificNameWithoutAuthor', '')

            family_data = species_data.get('family', {})
            family = family_data.get('scientificNameWithoutAuthor', '')

            score = item.get('score', 0)

            plant = PlantIdentification(
                scientific_name=scientific_name,
                common_names=common_names,
                genus=genus,
                family=family,
                score=score,
                species=scientific_name_full
            )
            plants.append(plant)

        return plants

    def get_best_match(self, result: Dict) -> Optional[PlantIdentification]:
        plants = self.parse_identification_result(result)
        if plants:
            return plants[0]
        return None

    def get_predicted_organ(self, result: Dict) -> Optional[str]:
        if 'predictedOrgans' in result and result['predictedOrgans']:
            organ = result['predictedOrgans'][0].get('organ', '')
            if organ:
                organ_ru = {
                    'flower': 'цветок',
                    'leaf': 'лист',
                    'fruit': 'плод',
                    'bark': 'кору',
                    'auto': 'растение'
                }.get(organ, organ)
                return organ_ru
        return None

    def get_plant_info_for_bot(self, result: Dict) -> Optional[Dict]:
        best_match = self.get_best_match(result)
        if not best_match:
            return None

        organ_info = ""
        predicted_organ = self.get_predicted_organ(result)
        if predicted_organ:
            organ_info = f"🔍 Распознано по: {predicted_organ}"

        text = f"🌱 *Распознано растение:* {best_match.scientific_name}\n\n"

        if best_match.common_names:
            common_names_str = ', '.join(best_match.common_names[:3])
            text += f"*Названия:* {common_names_str}\n"

        text += f"*Семейство:* {best_match.family}\n"
        text += f"*Род:* {best_match.genus}\n"
        text += f"*Достоверность:* {best_match.score:.2%}\n"

        if organ_info:
            text += f"\n{organ_info}"

        return {
            'text': text,
            'scientific_name': best_match.scientific_name,
            'common_names': best_match.common_names,
            'family': best_match.family,
            'genus': best_match.genus,
            'score': best_match.score
        }

def download_image_from_telegram(bot, file_id: str, save_path: str) -> bool:
    """Скачивает изображение из Telegram"""
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(save_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        return True
    except Exception as e:
        print(f"Ошибка при скачивании изображения: {e}")
        return False


def cleanup_temp_files(file_paths: List[str]):
    """Удаляет временные файлы"""
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Ошибка при удалении файла {file_path}: {e}")