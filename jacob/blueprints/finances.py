import os
import re

import hyperjson
from loguru import logger
from vkwave.api import API
from vkwave.bots import DefaultRouter
from vkwave.bots import MessageFromConversationTypeFilter
from vkwave.bots import SimpleBotEvent
from vkwave.bots import simple_bot_message_handler
from vkwave.client import AIOHTTPClient

from database import utils as db
from database.models import Chat
from database.models import FinancialCategory
from services import filters
from services import keyboard as kbs
from services.finances import generate_debtors_call
from services.logger.config import config

finances_router = DefaultRouter()
api_session = API(tokens=os.getenv("VK_TOKEN"), clients=AIOHTTPClient())
api = api_session.get_context()
logger.configure(**config)


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "finances"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def finances(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        await ans.answer(
            "Список финансовых категорий",
            keyboard=kbs.finances.list_of_fin_categories(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            ),
        )


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "create_finances_category"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def create_category(ans: SimpleBotEvent):
    db.shortcuts.update_admin_storage(
        db.students.get_system_id_of_student(ans.object.object.message.from_id),
        state_id=db.bot.get_id_of_state("wait_for_finances_category_description"),
    )
    await ans.answer(
        "Отправьте название категории и сумму сбора, разделенные пробелом",
        keyboard=kbs.common.cancel(),
    )


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "cancel"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def cancel_creating_category(ans: SimpleBotEvent):
    db.shortcuts.update_admin_storage(
        db.students.get_system_id_of_student(ans.object.object.message.from_id),
        state_id=db.bot.get_id_of_state("main"),
    )
    await ans.answer(
        "Создание категории отменено",
        keyboard=kbs.finances.list_of_fin_categories(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
        ),
    )


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("wait_for_finances_category_description"),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def register_category(ans: SimpleBotEvent):
    if re.match("^\w+ \d+$", ans.object.object.message.text):
        category = db.finances.create_finances_category(
            db.admin.get_active_group(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            ),
            *ans.object.object.message.text.split(),
        )
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
            state_id=db.bot.get_id_of_state("main"),
        )
        await ans.answer(
            f"Категория {category.name} зарегистрирована",
            keyboard=kbs.finances.list_of_fin_categories(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            ),
        )
    else:
        await ans.answer("Неверный формат данных")


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "fin_category"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def fin_category_menu(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        payload = hyperjson.loads(ans.object.object.message.payload)
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
            category_id=payload.get("category"),
        )

        if payload.get("category"):
            category_object = FinancialCategory.get_by_id(payload["category"])
        else:
            store = db.admin.get_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            category_object = FinancialCategory.get_by_id(store.category_id)

        category_name = category_object.name

        await ans.answer(
            f'Меню категории "{category_name}"',
            keyboard=kbs.finances.fin_category(),
        )


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "add_income"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def add_income(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
            state_id=db.bot.get_id_of_state("select_donater"),
        )
        await ans.answer(
            "Выберите студента, сдавшего деньги",
            keyboard=kbs.finances.IncomeNavigator(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            .render()
            .menu(),
        )


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "half"}) & filters.StateFilter("select_donater"),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def select_half(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        payload = hyperjson.loads(ans.object.object.message.payload)
        await ans.answer(
            "Выберите студента, сдавшего деньги",
            keyboard=kbs.finances.IncomeNavigator(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            .render()
            .submenu(payload["half"]),
        )


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "letter"}) & filters.StateFilter("select_donater"),
    MessageFromConversationTypeFilter("from_pm"),
)
async def select_letter(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        payload = hyperjson.loads(ans.object.object.message.payload)
        letter = payload["value"]
        await ans.answer(
            f"Список студентов на букву {letter}",
            keyboard=kbs.finances.IncomeNavigator(
                db.students.get_system_id_of_student(ans.object.object.message.peer_id),
            )
            .render()
            .students(letter),
        )


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "student"}) & filters.StateFilter("select_donater"),
    MessageFromConversationTypeFilter("from_pm"),
)
async def select_student(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        payload = hyperjson.loads(ans.object.object.message.payload)
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(
                ans.object.object.message.from_id,
            ),
            selected_students=str(payload["student_id"]),
            state_id=db.bot.get_id_of_state("enter_donate_sum"),
        )
        await ans.answer("Введите сумму дохода", keyboard=kbs.common.empty())


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("enter_donate_sum"),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def save_donate(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        text = ans.object.object.message.text
        if re.match(r"^\d+$", text):
            store = db.admin.get_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            db.finances.add_or_edit_donate(
                store.category_id,
                int(store.selected_students),
                int(text),
            )
            db.shortcuts.clear_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            await ans.answer("Доход сохранен", keyboard=kbs.finances.fin_category())
        else:
            await ans.answer("Введите только число")


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "show_debtors"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def call_debtors(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        if db.chats.get_list_of_chats_by_group(
            db.admin.get_active_group(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            ),
        ):
            msgs = generate_debtors_call(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            db.shortcuts.update_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
                state_id=db.bot.get_id_of_state("confirm_debtors_call"),
            )
            store = db.admin.get_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            chat_id = Chat.get_by_id(store.current_chat_id).chat_id
            chat_object = await api.messages.get_conversations_by_id(chat_id)
            try:
                chat_title = chat_object.response.items[0].chat_settings.title
            except IndexError:
                chat_title = "???"
            for msg in msgs:
                await ans.answer(msg)
            if len(msgs) > 1:
                text = f"Сообщения будут отправлены в {chat_title}"
            else:
                text = f"Сообщение будет отправлено в {chat_title}"
            await ans.answer(
                text,
                keyboard=kbs.finances.confirm_debtors_call(),
            )
        else:
            await ans.answer(
                "У вашей группы нет зарегистрированных чатов. Возврат в главное меню",
                keyboard=kbs.finances.fin_category(),
            )


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("confirm_debtors_call"),
    filters.PLFilter({"button": "chat_config"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def select_chat_debtors(ans: SimpleBotEvent):
    kb = await kbs.common.list_of_chats(
        db.students.get_system_id_of_student(ans.object.object.message.from_id),
    )
    await ans.answer("Выберите чат", keyboard=kb.get_keyboard())


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("confirm_debtors_call"),
    filters.PLFilter({"button": "chat"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def save_chat_debtors(ans: SimpleBotEvent):
    payload = hyperjson.loads(ans.object.object.message.payload)
    db.shortcuts.update_admin_storage(
        db.students.get_system_id_of_student(ans.object.object.message.from_id),
        current_chat_id=payload["chat_id"],
    )
    await call_debtors(ans)


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("confirm_debtors_call"),
    filters.PLFilter({"button": "confirm"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def confirm_call_debtors(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        msgs = generate_debtors_call(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
        )
        chat = db.shortcuts.get_active_chat(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
        ).chat_id
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
            state_id=db.bot.get_id_of_state("main"),
        )
        for msg in msgs:
            await api.messages.send(peer_id=chat, message=msg, random_id=0)
        await ans.answer("Призыв отправлен", keyboard=kbs.finances.fin_category())


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("confirm_debtors_call"),
    filters.PLFilter({"button": "deny"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def deny_call_debtors(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
            state_id=db.bot.get_id_of_state("main"),
        )
        await ans.answer("Отправка отменена", keyboard=kbs.finances.fin_category())


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "add_expense"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def add_expense(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        db.shortcuts.update_admin_storage(
            db.students.get_system_id_of_student(ans.object.object.message.from_id),
            state_id=db.bot.get_id_of_state("enter_expense_summ"),
        )
        await ans.answer("Введите сумму расхода")


@simple_bot_message_handler(
    finances_router,
    filters.StateFilter("enter_expense_summ"),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def save_expense(ans: SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        text = ans.object.object.message.text
        if re.match(r"^\d+$", text):
            store = db.admin.get_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            db.finances.add_expense(store.category_id, int(text))
            db.shortcuts.clear_admin_storage(
                db.students.get_system_id_of_student(ans.object.object.message.from_id),
            )
            await ans.answer("Расход сохранен", keyboard=kbs.finances.fin_category())
        else:
            await ans.answer("Введите только число")


@simple_bot_message_handler(
    finances_router,
    filters.PLFilter({"button": "show_stats"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def get_statistics(ans: SimpleBotEvent):
    store = db.admin.get_admin_storage(
        db.students.get_system_id_of_student(ans.object.object.message.from_id),
    )
    donates_summ = db.finances.calculate_donates_in_category(store.category_id)
    expenses_summ = db.finances.calculate_expenses_in_category(store.category_id)
    await ans.answer(
        f"Статистика\nСобрано: {donates_summ} руб.\nПотрачено: {expenses_summ} руб.",
    )
