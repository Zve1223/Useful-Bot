import os
import asyncio

import cv2
from pyzbar import pyzbar
import soundfile as sf
import speech_recognition as sr
from langdetect import detect
from language_tool_python import LanguageTool
from deep_translator import GoogleTranslator as Translator
from gtts import gTTS
from qrcode import QRCode
from qrcode.exceptions import DataOverflowError
from pycbrf import ExchangeRates
from datetime import datetime

general_path = os.path.abspath('./files')

lists_path = os.path.join(general_path, 'lists')

IETF_path = os.path.join(lists_path, 'IETF.txt')
ISO4217_path = os.path.join(lists_path, 'ISO4217.txt')

IETF_full = []
IETF_code = []
ISO4217_full = []
ISO4217_code = []
ISO4217_num = []

IETF_code_to_lang = {}
ISO4217_code_to_currency = {}
ISO4217_num_to_currency = {}

recognize_path = os.path.join(general_path, 'recognize')
voice_path = os.path.join(general_path, 'voice')
make_qr_path = os.path.join(general_path, 'make_qr')
read_qr_path = os.path.join(general_path, 'read_qr')

directions = [recognize_path, voice_path, make_qr_path, read_qr_path]


# Вспомогательная функция для вычисления размера всех файлов
def get_files_size() -> int:
    total_size = 0
    for path, _, files in os.walk(general_path):
        for file in files:
            filepath = os.path.join(path, file)
            total_size += os.path.getsize(filepath)
    return total_size


# Проверяет на существоание всех папок, если их нет - создаёт
def check_dirs() -> None:
    print('--Начало проверки на наличие всех рабочих папок')
    for direction in directions:
        if not os.path.exists(direction):
            os.makedirs(direction)
            print(f'----Папка {direction} была успешно создана')
    print('--Все недостающие папки были успешно созданы\n\n')


# Очищает все папки
def clear() -> None:
    for direction in directions:
        print('--Начало очистки всех рабочих папок')
        print(f'----Начало очистки папки по пути {direction}')
        for filename in os.listdir(direction):
            filepath = os.path.join(direction, filename)
            os.remove(filepath)
            print(f'------Файл {filename} по пути {filepath} был успешно удалён')
        print(f'----Папка по пути {direction} была успешно очищена')

    print('--Все рабочие папки были успешно очищены\n\n')


def on_start() -> None:
    global IETF_path, ISO4217_path

    IETF_full.extend(open(IETF_path, 'r', encoding='UTF-8').read().split('\n'))
    IETF_temp = [[j for j in i.split() if j] for i in IETF_full]

    IETF_code.extend([i[1] for i in IETF_temp])

    ISO4217_full.extend(open(ISO4217_path, 'r', encoding='UTF-8').read().split('\n'))
    ISO4217_temp = [[j for j in i.split() if j] for i in ISO4217_full]

    ISO4217_code.extend([i[1] for i in ISO4217_temp])
    ISO4217_num.extend([i[2] for i in ISO4217_temp])

    for code, lang in [(k[1], ' '.join(k[3:])) for k in IETF_temp]:
        IETF_code_to_lang[code] = lang

    for code, num, currency in [(k[1], k[2], ' '.join(k[4:])) for k in IETF_temp]:
        ISO4217_code_to_currency[code] = currency
        ISO4217_num_to_currency[num] = currency


async def convert_to_wav(filepath: str) -> str:
    audio_data, sample_rate = sf.read(filepath)

    os.remove(filepath)

    filepath = '.'.join(filepath.split('.')[:-1]) + '.wav'
    sf.write(filepath, audio_data, sample_rate)

    return filepath


async def recognize(filename: str) -> str:
    filepath = os.path.join(recognize_path, filename)
    filepath = await convert_to_wav(filepath)

    r = sr.Recognizer()
    with sr.AudioFile(filepath) as source:
        audio = r.record(source)

    try:
        text = list(r.recognize_google(audio, language='ru-RU'))
        i = 2
        while i < len(text):
            if text[i].isupper():
                text.insert(i - 1, '.')
                i += 1
            i += 1
        text[0] = text[0].upper()
        text = ''.join(text) + '.'
        text = await ortho(text)
        return text[0]
    except sr.UnknownValueError:
        print('Google Speech Recognition не смог распознать речь')
        return 'Google Speech Recognition не смог распознать речь'
    except sr.RequestError as e:
        print(f'Ошибка {e} в работе Google Speech Recognition API')
        return f'Ошибка {e} в работе Google Speech Recognition API'


async def voice(text: str, filename: str, lang: str, slow: bool = False) -> int:
    filepath = os.path.join(voice_path, filename)

    while os.path.exists(filepath):
        await asyncio.sleep(0.25)

    try:
        audio = gTTS(text, lang=lang, slow=slow)
        audio.save(filepath)
    except ValueError:
        return 1

    return 0


b = []


async def translate(text: str, to_lang: str) -> str:
    to_lang = to_lang.lower()
    if to_lang not in IETF:
        return 'Ошибка: Неверный формат языка'

    try:
        t = Translator(target=to_lang)
        text = t.translate(text)
    except Exception as e:
        if str(e) == 'invalid destination language':
            b.append(to_lang)
        print('----' + str(e))
        return 'Ошибка: не удалось перевести текст'

    return text


async def ortho(text: str) -> tuple[str, list[tuple[str, str, str]], list[tuple[str, str]]]:
    tool = LanguageTool(detect(text))
    text = tool.correct(text)
    matches = []
    optional = []
    for i in tool.check(text):
        sentence = i.__dict__['sentence']
        corrected = i.matchedText
        replacements = i.__dict__['replacements']
        if len(replacements) != 0:
            correct = replacements[0]
            matches.append((sentence, corrected, correct))
        else:
            optional.append((sentence, corrected))

    return text, matches, optional


async def make_qr(data: str, filename: str) -> int:
    filepath = os.path.join(make_qr_path, filename)

    while os.path.exists(filepath):
        await asyncio.sleep(0.25)

    try:
        qr = QRCode(border=1)
        qr.add_data(data)
        qr.make()
        img = qr.make_image()
    except DataOverflowError:
        return -1

    img.save(filepath)

    return 0


async def read_qr(filename: str) -> str:
    filepath = os.path.join(read_qr_path, filename)

    image = cv2.imread(filepath)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    barcodes = pyzbar.decode(gray)

    if len(barcodes) == 0:
        return 'Не удалось распознать QR-код'

    return ''.join([barcode.data.decode('UTF-8') for barcode in barcodes])


async def exchange(of: str, to: str = 'RUB', date: datetime | str | None = None) -> str:
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    elif isinstance(date, datetime):
        date = date.strftime('%Y-%m-%d')
    else:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e:
            print(f'--Неверный формат даты:\n' + '\n'.join(['--' + i for i in str(e).split('\n')]))
            return 'Ошибка: Неверный формат даты'

    rates = ExchangeRates(date)

    if (of not in ISO4217_code and of not in ISO4217_num) or (to not in ISO4217_code and to not in ISO4217_num):
        print('--Неверный формат валюты')
        return 'Ошибка: Неверный формат валюты'

    try:
        if of == to:
            return '1.0'
        elif of == 'RUB' or of == '643':
            return str(1.0 / float(rates[to].rate))
        elif to == 'RUB' or to == '643':
            return str(rates[of].rate)
        else:
            return str(rates[of].rate / rates[to].rate)
    except ValueError as e:
        print(f'--Не удалось перевести валюту:\n' + '\n'.join(['--' + i for i in str(e).split('\n')]))
        return 'Ошибка: Не удалось перевести валюту'
