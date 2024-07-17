import os
import time

from interactor import *
from states import *

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InputFile, \
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import exceptions

MEMORY_STORAGE = MemoryStorage()

TOKEN = open('./token.txt', 'r', encoding='UTF-8').read()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot, storage=MEMORY_STORAGE)

OPTIONS = '''/recognize — Распознать голос
/voice — Озвучить текст
/translate — Перевести текст
/ortho — Проверить текст на ошибки
/make_qr — Сделать QR-код
/read_qr — Считать QR-код
/exchange — Посмотреть курс валюты

/back - Отменить все действия'''

main_keyboard = ReplyKeyboardMarkup()
main_keyboard.row(KeyboardButton('/help'))
main_keyboard.row(KeyboardButton('/recognize'),
                  KeyboardButton('/voice'))
main_keyboard.row(KeyboardButton('/translate'),
                  KeyboardButton('/ortho'))
main_keyboard.row(KeyboardButton('/make_qr'),
                  KeyboardButton('/read_qr'))
main_keyboard.add(KeyboardButton('/exchange'))

help_keyboard = InlineKeyboardMarkup()
help_keyboard.row(InlineKeyboardButton('📚 /help', callback_data='/help'))
help_keyboard.row(InlineKeyboardButton('👂 /recognize', callback_data='/recognize'),
                  InlineKeyboardButton('👄 /voice', callback_data='/voice'))
help_keyboard.row(InlineKeyboardButton('🈺 /translate', callback_data='/translate'),
                  InlineKeyboardButton('📝 /ortho', callback_data='/ortho'))
help_keyboard.row(InlineKeyboardButton('🏞 /make_qr', callback_data='/make_qr'),
                  InlineKeyboardButton('👀 /read_qr', callback_data='/read_qr'))
help_keyboard.row(InlineKeyboardButton('💰 /exchange', callback_data='/exchange'))

back_keyboard = InlineKeyboardMarkup()
back_keyboard.add(InlineKeyboardButton('🔙 /back', callback_data='/back'))

IETF = []   # Исправить


async def start_command(message: Message) -> None:
    with open('users.txt', 'r', encoding='UTF-8') as file:
        users = file.read()

    if str(message.from_id) not in users.split('\n'):
        users += '\n' + str(message.from_id)
        await message.answer('Вот, что я могу:\n\n' + OPTIONS, reply_markup=main_keyboard)

    with open('users.txt', 'w', encoding='UTF-8') as file:
        file.write(users.strip())


async def help_command(message: Message) -> None:
    await message.answer('Вот, что я могу:\n\n' + OPTIONS, reply_markup=help_keyboard)


# ----------------Блок функций для команд админов----------------


async def count_command(message: Message) -> None:
    if await is_admin(message.from_id):
        with open('users.txt', 'r') as file:
            await message.answer(f'Участников, опробовавших бота: {len(file.readlines())}')


async def size_command(message: Message) -> None:
    if await is_admin(message.from_id):
        await message.answer(f'Размер всех временных файлов на текущий момент: {get_files_size()} байт')


async def clear_command(message: Message) -> None:
    if await is_admin(message.from_id):
        clear()
        await message.answer('Все временные файлы были успешно удалены')


async def state_command(message: Message, state: FSMContext) -> None:
    if await is_admin(message.from_id):
        await message.answer(str(await state.get_state()))


# ----------------Блок вспомогательных функций----------------


# Вспомогательная функция для проверки является ли пользователь админом по его id
async def is_admin(user_id: int) -> bool:
    with open('admins.txt', 'r') as file:
        return str(user_id) in map(lambda s: s.split('#')[0].strip(), file.read().split('\n'))


# ----------------Блок функций распознавания речи----------------


async def send_recognized(message: Message) -> None:
    temp = await message.answer('Начало распознавания речи...')

    if message.voice:
        file_id = message.voice.file_id
    else:
        file_id = message.audio.file_id

    file = await bot.get_file(file_id)

    filename = str(message.from_id) + '.wav'
    filepath = os.path.join(recognize_path, filename)
    while os.path.exists(filepath):
        await asyncio.sleep(0.25)

    try:
        await bot.download_file(file.file_path, filepath)
    except exceptions.FileIsTooBig:
        await message.answer('Ошибка: размер файла превышает допустимое значение',
                             reply_markup=back_keyboard)
        return

    text = await recognize(filename)
    await message.answer(text)
    await temp.delete()

    os.remove(filepath)


async def recognize_command(message: Message) -> None:
    await message.answer('Отправьте аудио-файл для распознания текста',
                         reply_markup=back_keyboard)
    await RecognizeSteps.GET_VOICE.set()


async def recognize_get_voice(message: Message, state: FSMContext) -> None:
    await send_recognized(message)
    await state.finish()


# ----------------Блок функций распознавания речи----------------


async def send_voiced(message: Message, text: str, lang: str = '') -> None:
    temp = await message.answer('Начало озвучки текста...')

    filename = str(message.from_id) + '.wav'
    filepath = os.path.join(voice_path, filename)

    if lang == '':
        try:
            lang = detect(message.text)
        except ValueError:
            await message.answer('При автоматическом определении языка возникли некоторые проблемы\n'
                                 'Был выбран язык по умолчанию: Русский язык')
            lang = 'ru'

    if lang not in IETF:
        await temp.delete()
        await message.answer('Ошибка: неизвестный язык')
        return

    result = await voice(text, filename, lang)

    if result == 1:
        await message.answer(IETF_code_to_lang[lang] + ' не может быть озвучен\n'
                                                  'Был выбран язык по умолчанию: Русский язык')
        await voice(text, filename, 'ru')

    file = InputFile(filepath, filename=filename)

    await message.answer_voice(file)
    await temp.delete()

    os.remove(filepath)


async def voice_command(message: Message) -> None:
    await VoiceSteps.GET_TEXT.set()
    await message.answer('Отправьте текст для озвучки',
                         reply_markup=back_keyboard)


voice_choose_keyboard = InlineKeyboardMarkup()
voice_choose_keyboard.row(InlineKeyboardButton('🤖 /auto', callback_data='/auto'),
                          InlineKeyboardButton('🔎 /choose', callback_data='/choose'))
voice_choose_keyboard.row(InlineKeyboardButton('🔙 /back', callback_data='/back'))


async def voice_get_text(message: Message, state: FSMContext) -> None:
    if any(letter.isalpha() for letter in message.text) is False:
        await message.answer('В сообщение не было обнаружено текста, попробуйте ещё раз',
                             reply_markup=back_keyboard)
        return

    async with state.proxy() as data:
        data['text'] = message.text

    await message.answer('Выберите способ выбора языка:\n'
                         '/auto — определить язык автоматически\n'
                         '/choose — выбрать язык вручную',
                         reply_markup=voice_choose_keyboard)
    await VoiceSteps.ASK_METHOD.set()


async def voice_make_choice(message: Message, state: FSMContext, choice: str) -> None:
    match choice:
        case '/auto':
            await voice_auto_detect(message, state)
        case '/choose':
            await message.answer('Пожалуйста, введите тег нужного вам языка (см. в списке)\n'
                                 '\n'
                                 'Доступные языки для озвучки:\n'
                                 'af, ar, bg, bn, bs, ca, cs, da, de, el, en, es, et, fi, fr, gu, hi, hr, hu, id, is, '
                                 'it, ja, km, kn, ko, lv, ml, mr, ms, my, ne, nl, no, pl, pt, ro, ru, si, sk, sq, sr, '
                                 'sv, sw, ta, te, th, tr, uk, ur, vi, zh'
                                 '\n'
                                 'Подробнее о тегах на сайте:'
                                 'https://en.wikipedia.org/wiki/IETF_language_tag',
                                 reply_markup=back_keyboard)
            await VoiceSteps.CHOOSE_LANG.set()


async def voice_text_choice(message: Message, state: FSMContext) -> None:
    await voice_make_choice(message, state, message.text.split()[0])


async def voice_button_choice(call: CallbackQuery, state: FSMContext) -> None:
    await voice_make_choice(call.message, state, call.data)
    await call.answer()
    await call.message.delete()


async def voice_auto_detect(message: Message, state: FSMContext) -> None:
    try:
        async with state.proxy() as data:
            lang = detect(data['text'])
    except ValueError:
        await message.answer('При определении языка возникли некоторые проблемы')
        await voice_make_choice(message, state, '/choose')
        return

    async with state.proxy() as data:
        await send_voiced(message, data['text'], lang)
        await state.finish()


async def voice_choose_lang(message: Message, state: FSMContext) -> None:
    if message.text not in IETF:
        await message.answer('Язык не найден, пожалуйста, попробуйте снова',
                             reply_markup=back_keyboard)
        return

    async with state.proxy() as data:
        await send_voiced(message, data['text'], message.text)
        await state.finish()


# ----------------Блок функций перевода----------------


async def translate_command(message: Message) -> None:
    await message.answer('Отправьте текст для перевода',
                         reply_markup=back_keyboard)
    await TranslateSteps.GET_TEXT.set()


translate_choose_keyboard = InlineKeyboardMarkup()
translate_choose_keyboard.row(InlineKeyboardButton('👍 /yes', callback_data='/yes'),
                              InlineKeyboardButton('🔎 /choose', callback_data='/choose'))
translate_choose_keyboard.row(InlineKeyboardButton('🔙 /back', callback_data='/back'))


async def translate_get_text(message: Message, state: FSMContext) -> None:
    if any(letter.isalpha() for letter in message.text) is False:
        await message.answer('В сообщение не было обнаружено текста, попробуйте ещё раз',
                             reply_markup=back_keyboard)
        return

    async with state.proxy() as data:
        data['text'] = message.text

    try:
        lang_from = detect(message.text)
    except ValueError:
        await message.answer('При определение языка что-то пошло не так\n'
                             'Пожалуйста, введите тег языка текста (см. на сайте)\n'
                             '(https://en.wikipedia.org/wiki/IETF_language_tag)',
                             reply_markup=back_keyboard)
        await TranslateSteps.CHOOSE_LANG_FROM.set()
        return

    if lang_from not in IETF:
        await message.answer('Языка ' + lang_from + ' нет в списке доступных\n'
                             'Пожалуйста, введите тег языка текста (см. на сайте)\n'
                             '(https://en.wikipedia.org/wiki/IETF_language_tag)',
                             reply_markup=back_keyboard)
        await TranslateSteps.CHOOSE_LANG_FROM.set()

    async with state.proxy() as data:
        data['lang_from'] = lang_from

    await message.answer(f'Это {IETF_code_to_lang[lang_from]} ({lang_from})?', reply_markup=translate_choose_keyboard)


async def translate_make_choice(message: Message, state: FSMContext, choice: str) -> None:
    match choice:
        case '/yes':
            await TranslateSteps.CHOOSE_LANG_TO.set()
        case '/choose':
            await message.answer('Пожалуйста, введите тег языка текста (см. в списке)\n'
                                 '\n'
                                 'Подробнее о тегах на сайте:'
                                 'https://en.wikipedia.org/wiki/IETF_language_tag',
                                 reply_markup=back_keyboard)
            await TranslateSteps.CHOOSE_LANG_FROM.set()


async def translate_text_choice(message: Message, state: FSMContext) -> None:
    await translate_make_choice(message, state, message.text.split()[0])


async def translate_button_choice(call: CallbackQuery, state: FSMContext) -> None:
    await translate_make_choice(call.message, state, call.data)
    await call.answer()
    await call.message.delete()


# async def translate_choose_lang_from(message: Message, state: FSMContext) -> None:


async def send_corrected(message: Message) -> None:
    temp = await message.answer('Начало поиска и исправления ошибок...')

    corrected, matches, optional = await ortho(message.text)

    matches = [f'В предложение:\n'
               f'"{i[0]}"\n'
               f'Была найдена ошибка "{i[1]}"\n'
               f'И исправлена на "{i[2]}"' for i in matches]

    optional = [f'В предложение:\n'
                f'"{i[0]}"\n'
                f'Можно заменить слово "{i[1]}"' for i in optional]

    if len(matches) != 0:
        await message.answer(corrected)
        await message.answer('Все найденные и исправленные возможные ошибки:\n\n' + '\n\n'.join(matches))
    else:
        await message.answer('Ошибки в тексте не найдены')

    if len(optional) != 0:
        await message.answer('Для большей грамотности текста:\n\n' +
                             '\n\n'.join(optional) +
                             '\n\nНа что-то более подходящее')

    await temp.delete()


async def ortho_command(message: Message) -> None:
    await message.answer('Введите текст для исправления ошибок')
    await OrthoSteps.GET_TEXT.set()


async def ortho_get_text(message: Message, state: FSMContext) -> None:
    await send_corrected(message)
    await state.finish()


async def send_qr_code(message: Message) -> None:
    temp = await message.answer('Начало преобразования в QR-код...')

    filename = str(message.from_id) + '.png'
    filepath = os.path.join(make_qr_path, filename)

    result = await make_qr(message.text, filename)

    if result == -1:
        await message.answer('Ошибка: превышение объёма данных')
        await temp.delete()
        return

    file = InputFile(filepath, filename=filename)

    await message.answer_photo(file)
    await temp.delete()

    os.remove(filepath)


async def make_qr_command(message: Message) -> None:
    await message.answer('Отправьте текст для преобразования в QR-код')
    await MakeQRSteps.GET_DATA.set()


async def make_qr_get_data(message: Message, state: FSMContext) -> None:
    await send_qr_code(message)
    await state.finish()


async def send_read(message: Message) -> None:
    temp = await message.answer('Начало распознавания речи...')

    if message.photo:
        file_id = message.photo[0].file_id
    else:
        file_id = message.document.file_id

    file = await bot.get_file(file_id)

    filename = str(message.from_id) + '.wav'
    filepath = os.path.join(read_qr_path, filename)
    while os.path.exists(filepath):
        await asyncio.sleep(0.25)

    try:
        await bot.download_file(file.file_path, filepath)
    except exceptions.FileIsTooBig:
        await message.answer('Ошибка: размер файла превышает допустимое значение',
                             reply_markup=back_keyboard)
        return

    text = await read_qr(filename)
    await message.answer(text)
    await temp.delete()

    os.remove(filepath)


async def read_qr_command(message: Message) -> None:
    await message.answer('Отправьте фото с QR-кодом для его расшифровки')
    await ReadQRSteps.GET_IMAGE.set()


async def read_qr_get_image(message: Message, state: FSMContext) -> None:
    await send_read(message)
    await state.finish()


# ----------------Блок других функций----------------


# Функция для возврата к первоначальному машинному состоянию
async def back_command(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.delete()
        return
    await state.finish()
    await message.answer('Все действия успешно отменены')
    await message.delete()


async def choose_by_button(call: CallbackQuery, state: FSMContext) -> None:
    await back_command(call.message, state)
    match call.data:
        case '/recognize':
            await recognize_command(call.message)
        case '/voice':
            await voice_command(call.message)
        case '/translate':
            await call.message.answer('Данная функция временно не доступна')
        case '/ortho':
            await ortho_command(call.message)
        case '/make_qr':
            await make_qr_command(call.message)
        case '/read_qr':
            await make_qr_command(call.message)
        case '/exchange':
            await call.message.answer('Такой функции пока нет')
        case '/help':
            await help_command(call.message)
    await call.answer()


# ----------------Блок стартовых функций----------------


def register_all_handlers() -> None:
    dp.register_message_handler(start_command, commands=['start'], state=None)
    dp.register_message_handler(help_command, commands=['help'], state='*')

    dp.register_message_handler(count_command, commands=['count'], state='*')
    dp.register_message_handler(size_command, commands=['size'], state='*')
    dp.register_message_handler(clear_command, commands=['clear'], state='*')
    dp.register_message_handler(state_command, commands=['state'], state='*')

    dp.register_message_handler(recognize_command, commands=['recognize'], state=None)
    dp.register_message_handler(recognize_get_voice,
                                content_types=[types.ContentType.AUDIO, types.ContentType.VOICE],
                                state=RecognizeSteps.GET_VOICE)

    dp.register_message_handler(voice_command, commands=['voice'], state=None)
    dp.register_message_handler(voice_get_text, content_types=[types.ContentType.TEXT], state=VoiceSteps.GET_TEXT)
    dp.register_message_handler(voice_text_choice, commands=['auto', 'choose'], state=VoiceSteps.ASK_METHOD)
    dp.register_callback_query_handler(voice_button_choice, state=VoiceSteps.ASK_METHOD)
    dp.register_message_handler(voice_choose_lang, content_types=[types.ContentType.TEXT], state=VoiceSteps.CHOOSE_LANG)

    dp.register_message_handler(ortho_command, commands=['ortho'], state=None)
    dp.register_message_handler(ortho_get_text, content_types=[types.ContentType.TEXT], state=OrthoSteps.GET_TEXT)

    dp.register_message_handler(make_qr_command, commands=['make_qr'], state=None)
    dp.register_message_handler(make_qr_get_data, content_types=[types.ContentType.TEXT], state=MakeQRSteps.GET_DATA)

    dp.register_message_handler(read_qr_command, commands=['read_qr'], state=None)
    dp.register_message_handler(read_qr_get_image,
                                content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT],
                                state=ReadQRSteps.GET_IMAGE)

    dp.register_message_handler(back_command, commands=['back'], state='*')

    dp.register_message_handler(send_recognized,
                                content_types=[types.ContentType.AUDIO, types.ContentType.VOICE], state='*')
    dp.register_message_handler(read_qr_get_image,
                                content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT],
                                state='*')

    dp.register_callback_query_handler(choose_by_button, state='*')


async def start_bot() -> None:
    check_dirs()
    clear()
    on_start()
    register_all_handlers()

    try:
        await dp.start_polling()
    finally:
        await bot.session.close()


if __name__ == '__main__':
    a = '''af - Африкаанс
ak - Акан
am - Амхарский
ar - Арабский
as - Ассамский
ay - Аймара
az - Азербайджанский
be - Белорусский
bg - Болгарский
bho - Бходжпури
bm - Бамбара
bn - Бенгальский
bs - Боснийский
ca - Каталанский
ceb - Себуанский
ckb - Курдский (сорани)
co - Корсиканский
cs - Чешский
cy - Валлийский
da - Датский
de - Немецкий
doi - Догри
dv - Мальдивский
ee - Эве
el - Греческий
en - Английский
eo - Эсперанто
es - Испанский
et - Эстонский
eu - Баскский
fa - Персидский
fi - Финский
fr - Французский
fy - Фризский
ga - Ирландский
gd - Шотландский (гэльский)
gl - Галисийский
gn - Гуарани
gom - Гоанский
gu - Гуджарати
ha - Хауса
haw - Гавайский
hi - Хинди
hmn - Хмонг
hr - Хорватский
ht - Гаитянский креольский
hu - Венгерский
hy - Армянский
id - Индонезийский
ig - Игбо
ilo - Илокано
is - Исландский
it - Итальянский
iw - Иврит
ja - Японский
jw - Яванский
ka - Грузинский
kk - Казахский
km - Кхмерский
kn - Каннада
ko - Корейский
kri - Криольский
ku - Курдский
ky - Киргизский
la - Латынь
lb - Люксембургский
lg - Луганда
ln - Лингала
lo - Лаосский
lt - Литовский
lus - Мизо
lv - Латышский
mai - Майтхили
mg - Малагасийский
mi - Маори
mk - Македонский
ml - Малаялам
mn - Монгольский
mni-Mtei - Манипури (мэйтэй)
mr - Маратхи
ms - Малайский
mt - Мальтийский
my - Бирманский
ne - Непальский
nl - Нидерландский
no - Норвежский
nso - Сото северный
ny - Чиньянджа
om - Оромо
or - Ория
pa - Панджаби
pl - Польский
ps - Пушту
pt - Португальский
qu - Кечуа
ro - Румынский
ru - Русский
rw - Киньяруанда
sa - Санскрит
sd - Синдхи
si - Сингальский
sk - Словацкий
sl - Словенский
sm - Самоанский
sn - Шона
so - Сомали
sq - Албанский
sr - Сербский
st - Сото южный
su - Сунданский
sv - Шведский
sw - Суахили
ta - Тамильский
te - Телугу
tg - Таджикский
th - Тайский
ti - Тигринья
tk - Туркменский
tl - Тагальский
tr - Турецкий
ts - Чонга
tt - Татарский
ug - Уйгурский
uk - Украинский
ur - Урду
uz - Узбекский
vi - Вьетнамский
xh - Коса
yi - Идиш
yo - Йоруба
zh-CN - Китайский (упрощенный)
zh-TW - Китайский (традиционный)
zu - Зулу'''
    for n, i in enumerate([' '.join([j if j != '-' else '–' for j in i.split()]) for i in a.split('\n')]):
        b = f'{n + 1}. {i.split()[0]} - {i[i.index("–") + 2:]}'
        if b[-2] + b[-1] == 'ий':
            b += ' язык'
        else:
            b = b.split()
            b.insert(3, 'Язык')
            b = ' '.join(b)
        print(b)
    # asyncio.run(start_bot())
    # af, sq, am, ar, hy, as, ay, az, bm, eu, be, bn, bho, bs, bg, ca, ceb, ny, zh-CN, zh-TW, co, hr, cs, da, dv, doi, nl, en, eo, et, ee, tl, fi, fr, fy, gl, ka, de, el, gn, gu, ht, ha, haw, iw, hi, hmn, hu, is, ig, ilo, id, ga, it, ja, jw, kn, kk, km, rw, gom, ko, kri, ku, ckb, ky, lo, la, lv, ln, lt, lg, lb, mk, mai, mg, ms, ml, mt, mi, mr, mni-Mtei, lus, mn, my, ne, no, or, om, ps, fa, pl, pt, pa, qu, ro, ru, sm, sa, gd, nso, sr, st, sn, sd, si, sk, sl, so, es, su, sw, sv, tg, ta, tt, te, th, ti, ts, tr, tk, ak, uk, ur, ug, uz, vi, cy, xh, yi, yo, zu 133
