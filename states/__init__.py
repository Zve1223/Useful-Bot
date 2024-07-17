from aiogram.dispatcher.filters.state import State, StatesGroup


class RecognizeSteps(StatesGroup):
    GET_VOICE = State()


class VoiceSteps(StatesGroup):
    GET_TEXT = State()
    ASK_METHOD = State()
    CHOOSE_LANG = State()


class TranslateSteps(StatesGroup):
    GET_TEXT = State()
    ASK_LANG = State()
    CHOOSE_LANG_FROM = State()
    CHOOSE_LANG_TO = State()


class OrthoSteps(StatesGroup):
    GET_TEXT = State()


class MakeQRSteps(StatesGroup):
    GET_DATA = State()


class ReadQRSteps(StatesGroup):
    GET_IMAGE = State()


class ExchangeSteps(StatesGroup):
    GET_OF = State()
    GET_TO = State()
    GET_DATE = State()
