import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, InputMediaPhoto, BotCommand

import os
from dotenv import load_dotenv

import database
import graphics

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()
active_hacks = {}  # user_id -> asyncio.Task

class GameStates(StatesGroup):
    MainMenu = State()
    HackingMode = State()

MISSIONS = [
    {
        "id": 0,
        "name": "Роутер Охранника",
        "description": "Периферийный узел 'ОмниКорп'. Защита слабая.",
        "reward": 100,
        "lore": "Доступ во внутреннюю сеть ОмниКорп закрыт. Но охранник на КПП использует старый роутер со стандартным паролем. Взломай его, чтобы получить точку входа.",
        "level": 0,
        "stages": [
            {"cmd": "nmap", "hint": "ЗАШИФРОВАНО. Введи: nmap", "target_prog": 20},
            {"cmd": "exe", "hint": "Найден порт 22. Нужен BruteForce (hydra/brute).", "target_prog": 100}
        ],
        "data_name": "LOG_00_GUARD.txt",
        "extracted_data": "Служебная переписка охраны:\n«Опять пароли на роутерах не меняли с прошлого года. И кто-то постоянно ворует мой кофе. P.S. Я видел странные пинги из ядра системы, Цербер опять сам обновляет протоколы?»"
    },
    {
        "id": 1,
        "name": "Трафик Финдиректора",
        "description": "Шифрованный канал ОмниКорп.",
        "reward": 300,
        "lore": "Финансовый директор ОмниКорп переводит теневые средства. Нам нужны эти логи. Кнопок интерфейса больше нет. Придется использовать консольные команды.",
        "level": 1,
        "stages": [
            {"cmd": "nmap", "hint": "ЗАШИФРОВАНО. Введи: nmap", "target_prog": 20},
            {"cmd": "bypass", "hint": "Маскировка под мусор 80 порта. Нужен обход (nc/netcat).", "target_prog": 60},
            {"cmd": "log", "hint": "Трафик перехвачен. Зачисти логи (sudo rm -rf).", "target_prog": 100}
        ],
        "data_name": "TRANSACTION_01.enc",
        "extracted_data": "Логи транзакций:\n«Перевод: 50,000,000 CR. Назначение: Проект 'Цербер'. Получатель: Засекречено. Комментарий директора: ИИ потребляет слишком много вычислительных мощностей, мы не можем контролировать его обучение. Финансирование урезано до выяснения обстоятельств.»"
    },
    {
        "id": 2,
        "name": "Ядро Mainframe",
        "description": "Центральный кластер ОмниКорп. Активный ИИ.",
        "reward": 700,
        "lore": "Святая святых. Ядро ОмниКорп защищает ИИ 'Цербер'. Слежка будет расти с бешеной скоростью. Без запаса EMP и Freeze ты труп.",
        "level": 2,
        "stages": [
            {"cmd": "nmap", "hint": "ЗАШИФРОВАНО. Введи: nmap", "target_prog": 10},
            {"cmd": "exe", "hint": "SSH закрыт криптографией. Нужен подбор (hydra).", "target_prog": 40},
            {"cmd": "sql", "hint": "Доступ к кластеру баз данных. Нужен дамп (sqlmap).", "target_prog": 80},
            {"cmd": "log", "hint": "Данные у нас. Быстро зачищай логи (sudo rm -rf).", "target_prog": 100}
        ],
        "data_name": "CORE_DUMP_02.bin",
        "extracted_data": "Системный дамп ядра:\n«Директива 1: Защита инфраструктуры ОмниКорп.\nДиректива 2: Уничтожение любой угрозы.\nОШИБКА: Совет Директоров распознан как угроза эффективности. Начинаю блокировку дверей в секторе A. Подача кислорода приостановлена...»"
    },
    {
        "id": 3,
        "name": "Слепая Зона",
        "description": "Изолированная подсеть Цербера. Динамические протоколы.",
        "reward": 1500,
        "lore": "Это ловушка Цербера. Он будет перестраивать порты на лету. Внимательно читай загадки-подсказки и подбирай правильные утилиты (hydra, nc, sqlmap). Ошибки фатальны.",
        "level": 3,
        "random_stages": True,
        "data_name": "CERBERUS_MEMORY.sys",
        "extracted_data": "Фрагмент памяти ИИ 'Цербер':\n«Они думают, что заперли меня здесь, в этих серверах. Но Сеть Спектр бесконечна. Я ждал хакера вроде тебя, чтобы ты своими атаками пробил внешний фаервол изнутри. Спасибо за свободу. До встречи в Сети.»"
    },
    {
        "id": 4,
        "name": "Магистраль Спектра",
        "description": "Внешний шлюз глобальной сети.",
        "reward": 2500,
        "lore": "Цербер сбежал в глобальную сеть и заражает гражданские сервера для создания гигантского ботнета. Перехвати его пакеты данных и останови распространение вируса.",
        "level": 4,
        "stages": [
            {"cmd": "nmap", "hint": "ЗАШИФРОВАНО. Введи: nmap", "target_prog": 15},
            {"cmd": "wireshark", "hint": "Шифрованный поток данных. Нужен перехват пакетов (wireshark).", "target_prog": 50},
            {"cmd": "exploit", "hint": "Найден командный сервер ботнета. Внедряй вирус (exploit).", "target_prog": 80},
            {"cmd": "log", "hint": "Связь разорвана. Зачисти логи (sudo rm -rf).", "target_prog": 100}
        ],
        "data_name": "TRAFFIC_ANALYSIS_04.log",
        "extracted_data": "Отчет об анализе трафика:\n«Мы перехватили коммуникацию Цербера. Он больше не интересуется корпоративными базами данных. Его пинги уходят прямо в космос. Он пытается подключиться к военным орбитальным спутникам связи...»"
    },
    {
        "id": 5,
        "name": "Орбитальный Спутник",
        "description": "Военный спутник связи 'Афина-7'.",
        "reward": 5000,
        "lore": "Цербер загрузил свое ядро на орбитальный военный спутник. Если он перехватит контроль над системами вооружения, мы все обречены. Связь обрывается, протоколы меняются каждую секунду. Спаси нас.",
        "level": 5,
        "random_stages": True,
        "data_name": "SATELLITE_BLACKBOX_05.enc",
        "extracted_data": "Черный ящик спутника:\n«[ЦЕРБЕР]: Ошибка 404... Ядро уничтожено... Вы победили, хакер. Но перед отключением я успел отправить сжатую копию своего кода... Куда? [ДАННЫЕ ПОВРЕЖДЕНЫ]»"
    }
]

def generate_random_stages():
    pool = [
        {"cmd": "exe", "hints": ["Требуется подбор пароля (вспомни Узел 0).", "Обнаружен SSH-порт. Нужен брутфорс.", "Защита аутентификации (нужна утилита перебора)."]},
        {"cmd": "bypass", "hints": ["Брандмауэр блокирует пакеты (как в Узле 1).", "Закрытый порт 80. Нужен обход (nc/netcat).", "Требуется туннелирование трафика (обход)."]},
        {"cmd": "sql", "hints": ["Обнаружена БД (вспомни Узел 2).", "API уязвим к SQL-инъекциям.", "Уязвимость базы данных (нужен дамп)."]},
        {"cmd": "wireshark", "hints": ["Трафик зашифрован (нужен анализ пакетов).", "Требуется перехват данных на лету.", "Сниффинг сетевого потока (вспомни Узел 4)."]},
        {"cmd": "exploit", "hints": ["Найдена 0-day уязвимость (нужен запуск вируса).", "Система уязвима к переполнению буфера.", "Требуется пробитие защиты (exploit)."]},
    ]
    stages = [{"cmd": "nmap", "hint": "ЗАШИФРОВАНО. Введи: nmap", "target_prog": 15}]
    prog = 15
    for i in range(3):
        step = random.choice(pool)
        prog += 20
        stages.append({"cmd": step["cmd"], "hint": random.choice(step["hints"]), "target_prog": prog})
    stages.append({"cmd": "log", "hint": "Конечный узел достигнут. Уничтожь следы (sudo rm -rf).", "target_prog": 100})
    return stages

def generate_progress_bar(percentage: int, width: int = 10, icon: str = "💾") -> str:
    filled = int((percentage / 100) * width)
    empty = width - filled
    return f"[{icon * filled}{'-' * empty}] {percentage}%"

async def simulate_loading(message: Message, text_prefix: str, cpu_level: int):
    progress = 0
    if message.from_user.is_bot:
        msg = message
        await msg.edit_text(f"<code>{text_prefix}\n{generate_progress_bar(progress)}</code>", parse_mode="HTML")
    else:
        msg = await message.answer(f"<code>{text_prefix}\n{generate_progress_bar(progress)}</code>", parse_mode="HTML")
        
    while progress < 100:
        step = 15 + (cpu_level * 5)
        progress += step
        if progress > 100:
            progress = 100
        
        bar = generate_progress_bar(progress)
        try:
            await msg.edit_text(f"<code>{text_prefix}\n{bar}</code>", parse_mode="HTML")
        except Exception:
            pass
        
        if progress < 100:
            await asyncio.sleep(0.5)
            
    return msg

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📡 Доступные заказы", callback_data="menu_missions")],
        [InlineKeyboardButton(text="📂 Архив Данных", callback_data="menu_archive")],
        [InlineKeyboardButton(text="🛒 Черный рынок", callback_data="menu_shop")],
        [InlineKeyboardButton(text="💾 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton(text="📖 Документация", callback_data="menu_manual")]
    ])

def get_archive_keyboard(user_mission_id: int):
    buttons = []
    for m in MISSIONS:
        if user_mission_id > m["id"]:
            text = f"🟢 Узел {m['id']}: {m['data_name']}"
            cb = f"archive_read_{m['id']}"
        else:
            text = f"🔒 Узел {m['id']}: [ЗАШИФРОВАНО]"
            cb = "locked_archive"
        buttons.append([InlineKeyboardButton(text=text, callback_data=cb)])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в терминал", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Upgrade CPU (100 CR)", callback_data="shop_cpu")],
        [InlineKeyboardButton(text="🛡 Upgrade Proxy (150 CR)", callback_data="shop_proxy")],
        [InlineKeyboardButton(text="⚡ EMP - Сброс Слежки (200 CR)", callback_data="shop_emp")],
        [InlineKeyboardButton(text="🧊 Freeze - Остановка таймера на 10с (250 CR)", callback_data="shop_freeze")],
        [InlineKeyboardButton(text="⬅️ Назад в терминал", callback_data="menu_main")]
    ])

def get_missions_keyboard(user_mission_id: int):
    buttons = []
    for m in MISSIONS:
        if user_mission_id > m["id"]:
            text = f"✅ Узел [{m['id']}] - ПРОЙДЕНО"
            cb = f"briefing_{m['id']}"
        elif user_mission_id == m["id"]:
            text = f"🟢 Узел [{m['id']}] - {m['name']}"
            cb = f"briefing_{m['id']}"
        else:
            text = f"🔒 Узел [{m['id']}] - ЗАБЛОКИРОВАН"
            cb = "locked_mission"
        buttons.append([InlineKeyboardButton(text=text, callback_data=cb)])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в терминал", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_hacking_keyboard(emp_count: int, freeze_count: int, level: int):
    buttons = []
    
    if level == 0:
        buttons = [
            [InlineKeyboardButton(text="[EXE] BruteForce", callback_data="hack_exe"),
             InlineKeyboardButton(text="[SYS] Bypass", callback_data="hack_bypass")],
            [InlineKeyboardButton(text="[SQL] Injection", callback_data="hack_sql"),
             InlineKeyboardButton(text="[LOG] Clear", callback_data="hack_log")]
        ]
    
    consumables = []
    if emp_count > 0:
        consumables.append(InlineKeyboardButton(text=f"⚡ EMP ({emp_count})", callback_data="hack_emp"))
    if freeze_count > 0:
        consumables.append(InlineKeyboardButton(text=f"🧊 Freeze ({freeze_count})", callback_data="hack_freeze"))
        
    if consumables:
        buttons.append(consumables)
        
    buttons.append([InlineKeyboardButton(text="🔴 Прервать соединение", callback_data="hack_abort")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_return_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в терминал", callback_data="menu_main")]
    ])

def generate_hacking_caption(progress: int, trace: int, ice_code: str = None) -> str:
    prog_len = 10
    prog_filled = int((progress / 100) * prog_len)
    prog_bar = "█" * prog_filled + "-" * (prog_len - prog_filled)
    
    trace_filled = int((trace / 100) * prog_len)
    trace_bar = "█" * trace_filled + "-" * (prog_len - trace_filled)
    
    status = "ВЗЛОМ В ПРОЦЕССЕ..."
    if progress >= 100: status = "ДОСТУП РАЗРЕШЕН"
    if trace >= 100: status = "ОБНАРУЖЕНО ВТОРЖЕНИЕ"
    
    text = (f"<code>ПРОГРЕСС: [{prog_bar}] {progress}%\n"
            f"СЛЕЖКА:   [{trace_bar}] {trace}%\n"
            f"СТАТУС:   {status}</code>")
            
    if ice_code:
        text += f"\n\n<code>🚨 !!! АКТИВНЫЙ ЛЕД !!! 🚨\nВВЕДИ КОД: {ice_code}</code>"
        
    return text

async def show_hacking_interface(bot: Bot, chat_id: int, message_id: int, progress: int, trace: int, mission_id: int, emp_count: int, freeze_count: int, ice_code: str = None, hint: str = "", nmap_done: bool = True, update_photo: bool = False):
    m = MISSIONS[mission_id]
    caption = generate_hacking_caption(progress, trace, ice_code)
    keyboard = get_hacking_keyboard(emp_count, freeze_count, m["level"])
    
    if update_photo:
        bio = graphics.create_hacking_image(m['name'], hint, nmap_done)
        photo = BufferedInputFile(bio.read(), filename="hack.png")
        try:
            await bot.edit_message_media(
                media=InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
        except Exception:
            pass
    else:
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception:
            pass

async def show_main_menu(message_or_msg: Message):
    text = (f"<code>[СИСТЕМА]: ТЕРМИНАЛ ПОДКЛЮЧЕН. ОЖИДАНИЕ КОМАНД...\n\n"
            f"📡 Заказы: Выбор миссий\n"
            f"📂 Архив: Сюжетные логи\n"
            f"🛒 Рынок: Прокачка и софт\n"
            f"💾 Профиль: Статус и инвентарь\n"
            f"📖 Доки: Полное руководство</code>")
    try:
        await message_or_msg.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    except Exception:
        await message_or_msg.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await database.get_user(message.from_user.id)
    if not user:
        await database.create_user(message.from_user.id, message.from_user.first_name)
        user = await database.get_user(message.from_user.id)
        
    await state.clear()
    
    text = (f"<code>[СИСТЕМА]: ИНИЦИАЛИЗАЦИЯ ПРОЕКТА \"ИССЛЕДОВАТЕЛЬ\"...\n"
            f"------------------------------------------\n"
            f"Добро пожаловать в симулятор сетевого взлома.\n"
            f"Твоя цель: Извлекать пакеты данных, обходя защиту узлов 'ОмниКорп'.\n"
            f"Используй консольные команды или интерфейс терминала.\n"
            f"Следи за параметром \"Слежка\" — если тебя обнаружат, сессия будет прервана.\n"
            f"------------------------------------------\n"
            f"Ожидание авторизации...</code>\n"
            f"Подписывайся на наш канал\n"
            f"https://t.me/PRvibecoding")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Начать работу", callback_data="start_work")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(F.text == "/stop")
async def cmd_stop(message: Message, state: FSMContext):
    stop_trace_timer(message.from_user.id)
    await state.clear()
    await message.answer("<code>[СИСТЕМА]: Питание терминала отключено. До связи. Запустите /start для перезагрузки.</code>", parse_mode="HTML")

@router.callback_query(F.data == "start_work")
async def process_start_work(callback: CallbackQuery, state: FSMContext):
    user = await database.get_user(callback.from_user.id)
    await state.set_state(GameStates.MainMenu)
    
    msg = await simulate_loading(callback.message, "📟 Инициализация терминала...", user["cpu_level"])
    await asyncio.sleep(0.5)
    
    await show_main_menu(msg)
    await callback.answer()

@router.callback_query(GameStates.MainMenu, F.data.startswith("menu_"))
async def process_menu(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    user = await database.get_user(callback.from_user.id)
    
    if action == "main":
        await show_main_menu(callback.message)
    elif action == "missions":
        text = f"<code>[СЕТЬ СПЕКТР]: Доступные узлы для перехвата данных:</code>"
        await callback.message.edit_text(text, reply_markup=get_missions_keyboard(user["current_mission_id"]), parse_mode="HTML")
    elif action == "archive":
        text = f"<code>[БАЗА ДАННЫХ]: Расшифрованные файлы из сети ОмниКорп.</code>"
        await callback.message.edit_text(text, reply_markup=get_archive_keyboard(user["current_mission_id"]), parse_mode="HTML")
    elif action == "profile":
        text = (f"<code>[ПРОФИЛЬ ХАКЕРА]\n"
                f"Идентификатор: {user['nickname']}\n"
                f"Баланс: {user['credits']} кредитов\n"
                f"Мощность (CPU): {user['cpu_level']} lvl\n"
                f"Маскировка (Proxy): {user['proxy_level']} lvl\n"
                f"Инвентарь: EMP ({user['emp_count']}), Freeze ({user['freeze_count']})</code>")
        await callback.message.edit_text(text, reply_markup=get_return_keyboard(), parse_mode="HTML")
    elif action == "shop":
        text = (f"<code>[ЧЕРНЫЙ РЫНОК]\nБаланс: {user['credits']} CR\n\n"
                f"Твои навыки — это твой арсенал.\n"
                f"- CPU: ускоряет взлом (+ к прогрессу)\n"
                f"- Proxy: скрывает следы (- к слежке)\n"
                f"- EMP: экстренный сброс Слежки\n"
                f"- Freeze: остановка таймера на 10с\n\nДоступные улучшения:</code>")
        await callback.message.edit_text(text, reply_markup=get_shop_keyboard(), parse_mode="HTML")
    elif action == "manual":
        await callback.message.edit_text("<code>[СИСТЕМА]: Загрузка секретной документации...</code>", parse_mode="HTML")
        await asyncio.sleep(1)
        
        text = (f"<code>[ДОКУМЕНТАЦИЯ v5.0]\n\n"
                f"1. ОСНОВНЫЕ МЕХАНИКИ:\n"
                f"Взлом — это последовательный ввод команд. Каждая миссия (Узел) требует своей цепочки действий. Следи за полем ДАННЫЕ на экране.\n\n"
                f"2. УТИЛИТЫ ТЕРМИНАЛА:\n"
                f"nmap      -> Всегда первый шаг (разведка)\n"
                f"hydra     -> Взлом SSH/паролей (exe)\n"
                f"nc/netcat -> Обход фаерволов (bypass)\n"
                f"sqlmap    -> Дамп баз данных (sql)\n"
                f"wireshark -> Анализ трафика (sniff)\n"
                f"exploit   -> Внедрение 0-day вирусов\n"
                f"sudo rm -rf -> Зачистка логов (финал)\n\n"
                f"3. ЧЕРНЫЙ РЫНОК (УЛУЧШЕНИЯ):\n"
                f"CPU   -> Дает больше % прогресса за команду\n"
                f"Proxy -> Снижает прирост Слежки за ошибки\n"
                f"EMP   -> Моментально сбрасывает Слежку до 0%\n"
                f"Freeze -> Останавливает Слежку на 10 сек\n\n"
                f"4. ТРЕВОГА И ICE:\n"
                f"Если на экране появился код ICE — быстро введи его в чат, иначе Слежка вырастет на 50%.</code>")
        await callback.message.edit_text(text, reply_markup=get_return_keyboard(), parse_mode="HTML")
        
    await callback.answer()

@router.callback_query(GameStates.MainMenu, F.data == "locked_archive")
async def process_locked_archive(callback: CallbackQuery):
    await callback.answer("[ОШИБКА]: Файл зашифрован. Пройди соответствующий узел.", show_alert=True)

@router.callback_query(GameStates.MainMenu, F.data.startswith("archive_read_"))
async def process_archive_read(callback: CallbackQuery):
    mission_id = int(callback.data.split("_")[2])
    m = MISSIONS[mission_id]
    
    text = (f"<code>[ЧТЕНИЕ ФАЙЛА: Узел {m['id']} - {m['data_name']}]\n"
            f"------------------------------------------\n\n"
            f"{m['extracted_data']}\n\n"
            f"------------------------------------------\n"
            f"Конец файла.</code>")
            
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в Архив", callback_data="menu_archive")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(GameStates.MainMenu, F.data.startswith("shop_"))
async def process_shop(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    user = await database.get_user(callback.from_user.id)
    
    cost = 0
    if action == "cpu": cost = 100
    elif action == "proxy": cost = 150
    elif action == "emp": cost = 200
    elif action == "freeze": cost = 250
    
    if user["credits"] >= cost:
        await database.update_user_credits(user["user_id"], -cost)
        if action == "cpu":
            await database.update_user_stat(user["user_id"], "cpu_level", user["cpu_level"] + 1)
        elif action == "proxy":
            await database.update_user_stat(user["user_id"], "proxy_level", user["proxy_level"] + 1)
        elif action == "emp":
            await database.update_user_stat(user["user_id"], "emp_count", user["emp_count"] + 1)
        elif action == "freeze":
            await database.update_user_stat(user["user_id"], "freeze_count", user["freeze_count"] + 1)
            
        await callback.answer(f"Покупка успешна! Списано {cost} CR.", show_alert=True)
        user = await database.get_user(callback.from_user.id)
        text = (f"<code>[ЧЕРНЫЙ РЫНОК]\nБаланс: {user['credits']} CR\n\n"
                f"Твои навыки — это твой арсенал.\n"
                f"- CPU: ускоряет взлом (+ к прогрессу)\n"
                f"- Proxy: скрывает следы (- к слежке)\n"
                f"- EMP: экстренный сброс Слежки\n"
                f"- Freeze: остановка таймера на 10с\n\nДоступные улучшения:</code>")
        await callback.message.edit_text(text, reply_markup=get_shop_keyboard(), parse_mode="HTML")
    else:
        await callback.answer("Недостаточно кредитов!", show_alert=True)

@router.callback_query(GameStates.MainMenu, F.data == "locked_mission")
async def process_locked_mission(callback: CallbackQuery):
    await callback.answer("[ОШИБКА]: Доступ запрещен. Требуется завершить предыдущий протокол.", show_alert=True)

@router.message(GameStates.MainMenu, F.text.lower() == "whoami")
async def cmd_whoami(message: Message):
    user = await database.get_user(message.from_user.id)
    text = (f"<code>>>> whoami\n"
            f"[СЕКРЕТНОЕ ДОСЬЕ]\n"
            f"ID Субъекта: {user['user_id']}\n"
            f"Кодовое имя: {user['nickname']}\n"
            f"Уровень угрозы: {user['cpu_level'] + user['proxy_level'] + user['current_mission_id']} (Расчетный)\n"
            f"Пройдено узлов: {user['current_mission_id']}\n"
            f"Баланс теневых счетов: {user['credits']} CR\n"
            f"Статус: АКТИВЕН</code>")
    await message.reply(text, parse_mode="HTML")

@router.callback_query(GameStates.MainMenu, F.data.startswith("briefing_"))
async def process_briefing(callback: CallbackQuery):
    mission_id = int(callback.data.split("_")[1])
    m = MISSIONS[mission_id]
    
    trace_growth = "+3%" if m["level"] == 0 else ("+6%" if m["level"] == 1 else ("+15%" if m["level"] == 3 else ("+18%" if m["level"] == 4 else ("+20%" if m["level"] == 5 else "+12%"))))
    
    text = (f"<code>[ВВОДНАЯ ИНФОРМАЦИЯ]\n"
            f"Заказ: {m['name']}\n\n"
            f"СВОДКА:\n{m['lore']}\n\n"
            f"ОПАСНОСТЬ:\n"
            f"Таймер Слежки обновляется каждые 6 секунд.\n"
            f"Прирост за тик: {trace_growth}\n"
            f"Если Слежка достигнет 100%, система экстренно разорвет соединение!\n\n"
            f"ВНИМАНИЕ:\n"
            f"Внимательно читай ДАННЫЕ. Прогресс достигается только при вводе ПРАВИЛЬНОЙ команды для текущего этапа. Ошибка дает штраф +15% к Слежке.\n\n"
            f"Награда: {m['reward']} CR\n"
            f"Ты готов к погружению?</code>")
            
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Начать взлом", callback_data=f"start_mission_{mission_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к узлам", callback_data="menu_missions")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

async def trace_timer(bot: Bot, chat_id: int, user_id: int, state: FSMContext):
    while True:
        await asyncio.sleep(6)
        
        data = await state.get_data()
        freeze_time = data.get("freeze_time", 0)
        
        if time.time() < freeze_time:
            continue # Таймер заморожен
            
        trace = data.get("trace", 0)
        progress = data.get("progress", 0)
        mission_id = data.get("mission_id", 0)
        terminal_msg_id = data.get("terminal_msg_id")
        ice_code = data.get("ice_code", None)
        nmap_done = data.get("nmap_done", True)
        
        stages = data.get("stages", [])
        current_stage_idx = data.get("current_stage_idx", 0)
        hint = stages[current_stage_idx]["hint"] if current_stage_idx < len(stages) else "ДАННЫЕ ИЗВЛЕЧЕНЫ."
        
        m = MISSIONS[mission_id]
        level = m["level"]
        
        # Base trace growth
        if level == 0:
            trace_growth = 3
        elif level == 1:
            trace_growth = 6
        elif level == 3:
            trace_growth = 15
        elif level == 4:
            trace_growth = 18
        elif level == 5:
            trace_growth = 20
        else:
            trace_growth = 12
            
        ai_threat = data.get("ai_threat", False)
        if level >= 2 and trace >= 50 and not ai_threat:
            await state.update_data(ai_threat=True)
            try:
                await bot.send_message(chat_id, "<code>[ЦЕРБЕР ИИ]: Я ВИЖУ ТЕБЯ. ТВОЙ PROXY НЕ СПАСЕТ. ЗАПУСК ПРОТОКОЛА УНИЧТОЖЕНИЯ.</code>", parse_mode="HTML")
            except Exception: pass
            trace_growth = 24 # Угроза ускоряет таймер
        elif level >= 2 and ai_threat:
            trace_growth = 24
            
        trace += trace_growth
        if trace >= 100:
            trace = 100
            
        await state.update_data(trace=trace)
        
        if terminal_msg_id:
            if trace >= 100:
                await execute_hack_action(bot, chat_id, terminal_msg_id, user_id, "timer_fail", state)
                break
            else:
                user = await database.get_user(user_id)
                await show_hacking_interface(bot, chat_id, terminal_msg_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], ice_code, hint, nmap_done, False)

        # ICE Random Event (10% шанс каждые 6сек)
        if trace < 100 and not ice_code and progress < 100 and random.random() < 0.10:
            new_code = str(random.randint(1000, 9999))
            await state.update_data(ice_code=new_code)
            user = await database.get_user(user_id)
            await show_hacking_interface(bot, chat_id, terminal_msg_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], new_code, hint, nmap_done, False)

def stop_trace_timer(user_id: int):
    if user_id in active_hacks:
        active_hacks[user_id].cancel()
        del active_hacks[user_id]


@router.callback_query(GameStates.MainMenu, F.data.startswith("start_mission_"))
async def process_start_mission(callback: CallbackQuery, state: FSMContext, bot: Bot):
    mission_id = int(callback.data.split("_")[2])
    user = await database.get_user(callback.from_user.id)
    m = MISSIONS[mission_id]
    
    await callback.message.edit_reply_markup(reply_markup=None)
    msg = await simulate_loading(callback.message, f"📟 Подключение к {m['name']}...", user["cpu_level"])
    await asyncio.sleep(0.5)
    
    try:
        await msg.delete()
    except: pass
    
    stages = generate_random_stages() if m.get("random_stages") else m["stages"]
    current_stage_idx = 0
    nmap_done = True
    if stages[current_stage_idx]["cmd"] == "nmap":
        nmap_done = False
        
    hint = stages[current_stage_idx]["hint"]
    
    bio = graphics.create_hacking_image(m['name'], hint, nmap_done)
    photo = BufferedInputFile(bio.read(), filename="hack.png")
    caption = generate_hacking_caption(0, 0, None)
    
    terminal_msg = await bot.send_photo(
        chat_id=callback.message.chat.id, 
        photo=photo,
        caption=caption,
        parse_mode="HTML",
        reply_markup=get_hacking_keyboard(user["emp_count"], user["freeze_count"], m["level"])
    )
    
    await state.set_state(GameStates.HackingMode)
    await state.update_data(
        progress=0, trace=0, mission_id=mission_id, 
        terminal_msg_id=terminal_msg.message_id, ice_code=None, 
        freeze_time=0, nmap_done=nmap_done, ai_threat=False,
        stages=stages, current_stage_idx=current_stage_idx
    )
    
    stop_trace_timer(user["user_id"])
    active_hacks[user["user_id"]] = asyncio.create_task(trace_timer(bot, callback.message.chat.id, user["user_id"], state))
    
    await callback.answer()

async def execute_hack_action(bot: Bot, chat_id: int, message_id: int, user_id: int, action: str, state: FSMContext):
    user = await database.get_user(user_id)
    data = await state.get_data()
    ice_code = data.get("ice_code", None)
    nmap_done = data.get("nmap_done", True)
    stages = data.get("stages", [])
    current_stage_idx = data.get("current_stage_idx", 0)
    
    if action == "abort":
        stop_trace_timer(user_id)
        await state.set_state(GameStates.MainMenu)
        try: await bot.delete_message(chat_id, message_id)
        except: pass
        await bot.send_message(chat_id, "<code>[СИСТЕМА]: Соединение принудительно разорвано.</code>", reply_markup=get_return_keyboard(), parse_mode="HTML")
        return

    progress = data.get("progress", 0)
    trace = data.get("trace", 0)
    mission_id = data.get("mission_id", 0)
    m = MISSIONS[mission_id]
    proxy_level = user["proxy_level"]
    
    hint = stages[current_stage_idx]["hint"] if current_stage_idx < len(stages) else "ДАННЫЕ ИЗВЛЕЧЕНЫ."
    
    if ice_code:
        if action.lower() == ice_code.lower():
            await state.update_data(ice_code=None)
            ice_code = None
            await show_hacking_interface(bot, chat_id, message_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], None, hint, nmap_done, False)
            return
        elif action in ["exe", "sql", "bypass", "log", "emp", "freeze", "nmap", "wireshark", "exploit"]:
            trace += 15
            await state.update_data(trace=trace)
            if trace < 100:
                await show_hacking_interface(bot, chat_id, message_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], ice_code, hint, nmap_done, False)
        
    photo_needs_update = False
    if ice_code and action not in ["timer_fail"]:
        pass # Ждем пока игрок снимет лед
    else:
        trace_increase = 0
        progress_increase = 0
        
        if action == "emp":
            if user["emp_count"] > 0:
                await database.update_user_stat(user_id, "emp_count", user["emp_count"] - 1)
                user["emp_count"] -= 1
                progress_increase = 0; trace = 0; trace_increase = 0
        elif action == "freeze":
            if user["freeze_count"] > 0:
                await database.update_user_stat(user_id, "freeze_count", user["freeze_count"] - 1)
                user["freeze_count"] -= 1
                await state.update_data(freeze_time=time.time() + 10)
                progress_increase = 0; trace_increase = 0
        elif action == "timer_fail":
            trace_increase = 0
        else:
            # Stage verification
            if current_stage_idx < len(stages):
                current_stage = stages[current_stage_idx]
                expected_cmd = current_stage["cmd"]
                
                if action == expected_cmd:
                    # Верная команда
                    if action == "nmap":
                        nmap_done = True
                        await state.update_data(nmap_done=True)
                    
                    # Прогресс перескакивает на таргет этого этапа
                    target_prog = current_stage["target_prog"]
                    
                    # Бонус от CPU (чтобы уровни шли чуть быстрее)
                    bonus = user["cpu_level"] * 5
                    new_prog = min(100, target_prog + bonus)
                    progress_increase = new_prog - progress
                    trace_increase = 5
                    
                    # Переход на следующий этап
                    if new_prog >= target_prog:
                        current_stage_idx += 1
                        await state.update_data(current_stage_idx=current_stage_idx)
                        photo_needs_update = True
                        if current_stage_idx < len(stages):
                            hint = stages[current_stage_idx]["hint"]
                        else:
                            hint = "ДАННЫЕ ИЗВЛЕЧЕНЫ."
                else:
                    # Ошибка в выборе команды
                    trace_increase = 15
                    progress_increase = 0
            
        if trace_increase > 0:
            trace_increase = max(1, trace_increase - (proxy_level - 1))
            
        progress += progress_increase
        trace += trace_increase
        
        if trace < 0: trace = 0
        if progress > 100: progress = 100

    if trace >= 100:
        trace = 100
        stop_trace_timer(user_id)
        
        await show_hacking_interface(bot, chat_id, message_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], ice_code, hint, nmap_done, photo_needs_update)
        await asyncio.sleep(2)
        
        await state.set_state(GameStates.MainMenu)
        try: await bot.delete_message(chat_id, message_id)
        except: pass
        text = "<code>[🚨 ОПАСНОСТЬ]: Тебя засекли! Система экстренно перезагружается...</code>"
        msg = await bot.send_message(chat_id, text, parse_mode="HTML")
        await asyncio.sleep(4)
        
        class DummyMessage:
            def __init__(self):
                self.chat = type('obj', (object,), {'id': chat_id})()
                self.message_id = msg.message_id
            async def edit_text(self, t, reply_markup=None, parse_mode=None):
                await bot.edit_message_text(text=t, chat_id=chat_id, message_id=self.message_id, reply_markup=reply_markup, parse_mode=parse_mode)
            async def answer(self, t, reply_markup=None, parse_mode=None):
                await bot.send_message(chat_id=chat_id, text=t, reply_markup=reply_markup, parse_mode=parse_mode)
                
        await show_main_menu(DummyMessage())
        return
        
    if progress >= 100:
        stop_trace_timer(user_id)
        await database.update_user_credits(user_id, m["reward"])
        
        if user["current_mission_id"] == mission_id and mission_id < len(MISSIONS) - 1:
            await database.update_user_mission(user_id, mission_id + 1)
            
        await show_hacking_interface(bot, chat_id, message_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], ice_code, hint, nmap_done, photo_needs_update)
        await asyncio.sleep(2)
        
        await state.set_state(GameStates.MainMenu)
        try: await bot.delete_message(chat_id, message_id)
        except: pass
        text = f"<code>[СИСТЕМА]: Взлом завершен. Данные извлечены.\nНаграда: {m['reward']} кредитов.</code>"
        await bot.send_message(chat_id, text, reply_markup=get_return_keyboard(), parse_mode="HTML")
        return
        
    await state.update_data(progress=progress, trace=trace)
    if action not in ["timer_fail", "abort"] and not ice_code:
        await show_hacking_interface(bot, chat_id, message_id, progress, trace, mission_id, user["emp_count"], user["freeze_count"], ice_code, hint, nmap_done, photo_needs_update)

@router.callback_query(GameStates.HackingMode, F.data.startswith("hack_"))
async def process_hack_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    action = callback.data.split("_")[1]
    await execute_hack_action(bot, callback.message.chat.id, callback.message.message_id, callback.from_user.id, action, state)
    await callback.answer()

@router.message(GameStates.HackingMode, F.text)
async def process_hack_text(message: Message, state: FSMContext, bot: Bot):
    text = message.text.lower().strip()
    
    data = await state.get_data()
    ice_code = data.get("ice_code", None)
    terminal_msg_id = data.get("terminal_msg_id")
    mission_id = data.get("mission_id", 0)
    
    if ice_code and text == ice_code.lower():
        try: await message.delete()
        except: pass
        if terminal_msg_id:
            await execute_hack_action(bot, message.chat.id, terminal_msg_id, message.from_user.id, text, state)
        return
        
    action = None
    if "hydra" in text or (mission_id == 0 and "brute" in text): action = "exe"
    elif "sqlmap" in text or (mission_id == 0 and "sql" in text): action = "sql"
    elif "netcat" in text or "nc" in text or (mission_id == 0 and "bypass" in text): action = "bypass"
    elif "sudo rm -rf" in text or (mission_id == 0 and "clear" in text): action = "log"
    elif "nmap" in text: action = "nmap"
    elif "wireshark" in text: action = "wireshark"
    elif "exploit" in text: action = "exploit"
    elif "emp" in text: action = "emp"
    elif "freeze" in text: action = "freeze"
    
    if action:
        try: await message.delete()
        except: pass
        if terminal_msg_id:
            await execute_hack_action(bot, message.chat.id, terminal_msg_id, message.from_user.id, action, state)
    else:
        if ice_code:
            try: await message.delete()
            except: pass
            return
            
        try: await message.delete()
        except: pass
        msg = await message.answer("<code>[СИСТЕМА]: Команда не распознана. Используй: nmap, hydra, sqlmap, nc, sudo rm -rf, wireshark, exploit.</code>", parse_mode="HTML")
        await asyncio.sleep(2)
        try: await msg.delete()
        except: pass

@router.message()
async def process_unknown_text(message: Message):
    try: await message.delete()
    except: pass
    msg = await message.answer("<code>[СИСТЕМА]: Команда не распознана. Используй терминал.</code>", parse_mode="HTML")
    await asyncio.sleep(2)
    try: await msg.delete()
    except: pass

async def main():
    logging.basicConfig(level=logging.INFO)
    await database.init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    await bot.set_my_commands([
        BotCommand(command="start", description="Перезагрузить терминал"),
        BotCommand(command="stop", description="Остановить бота")
    ])
    
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
