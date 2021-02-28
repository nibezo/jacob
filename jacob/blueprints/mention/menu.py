"""Главное меню Призыва."""

import os
import random

import ujson
from loguru import logger
from vkwave import api, bots, client

from jacob.database import models  # TODO: (?)
from jacob.database.utils import students
from jacob.database.utils.storages import managers
from jacob.services import call, exceptions, filters
from jacob.services import keyboard as kbs
from jacob.services.logger import config as logger_config

call_menu_router = bots.DefaultRouter()
api_session = api.API(
    tokens=os.getenv("VK_CANARY_TOKEN"),
    clients=client.AIOHTTPClient(),
)
api_context = api_session.get_context()
logger.configure(**logger_config.config)


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.PLFilter({"button": "half"}),
    filters.StateFilter("common_select_student"),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _select_half(ans: bots.SimpleBotEvent):
    payload = ujson.loads(ans.object.object.message.payload)
    admin_id = students.get_system_id_of_student(ans.object.object.message.from_id)
    await ans.answer(
        "Выберите призываемых студентов",
        keyboard=kbs.call.CallNavigator(admin_id).render().submenu(payload["half"]),
    )


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.PLFilter({"button": "letter"}),
    filters.StateFilter("common_select_student"),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _select_letter(ans: bots.SimpleBotEvent):
    payload = ujson.loads(ans.object.object.message.payload)
    letter = payload["value"]
    admin_id = students.get_system_id_of_student(ans.object.object.message.from_id)
    await ans.answer(
        "Список студентов на букву {0}".format(letter),
        keyboard=kbs.call.CallNavigator(admin_id).render().students(letter),
    )


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.PLFilter({"button": "student"}),
    filters.StateFilter("common_select_student"),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _select_student(ans: bots.SimpleBotEvent):
    payload = ujson.loads(ans.object.object.message.payload)
    student_id = payload["student_id"]
    admin_id = students.get_system_id_of_student(ans.object.object.message.peer_id)
    mention_manager = managers.MentionStorageManager(admin_id)
    if student_id in mention_manager.get_mentioned_students():
        mention_manager.remove_from_mentioned(
            student_id,
        )
        label = "удален из списка призыва"
    else:
        mention_manager.append_to_mentioned_students(
            student_id,
        )
        label = "добавлен в список призыва"
    await ans.answer(
        "{0} {1}".format(payload["name"], label),
        keyboard=kbs.call.CallNavigator(
            admin_id,
        )
        .render()
        .students(payload["letter"]),
    )


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.PLFilter({"button": "save_selected"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _confirm_call(ans: bots.SimpleBotEvent):
    admin_id = students.get_system_id_of_student(ans.object.object.message.peer_id)
    msg = call.generate_message(admin_id)

    admin_storage = managers.AdminConfigManager(admin_id)
    mention_storage = managers.MentionStorageManager(admin_id)
    state_storage = managers.StateStorageManager(admin_id)

    chat_id = admin_storage.get_active_chat().chat_id
    query = await api_context.messages.get_conversations_by_id(chat_id)
    try:
        chat_settings = query.response.items[0].chat_settings
    except IndexError:
        chat_name = "???"
    else:
        chat_name = chat_settings.title
    if not msg and not mention_storage.get_attaches():
        raise exceptions.EmptyCallMessage("Сообщение призыва не может быть пустым")
    state_storage.update(
        state_id=state_storage.get_id_of_state("confirm_call"),
    )
    await ans.answer(
        'Сообщение будет отправлено в чат "{0}":\n{1}'.format(chat_name, msg),
        keyboard=kbs.call.call_prompt(
            admin_id,
        ),
        attachment=mention_storage.get_attaches() or "",
    )


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.PLFilter({"button": "call_all"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _call_them_all(ans: bots.SimpleBotEvent):
    admin_id = students.get_system_id_of_student(ans.object.object.message.peer_id)
    student = models.Student.get_by_id(admin_id)
    mentioned_list = [st.id for st in students.get_active_students(student.group_id)]
    mention_storage = managers.MentionStorageManager(admin_id)
    mention_storage.update_mentioned_students(mentioned_list)
    await _confirm_call(ans)


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.StateFilter("mention_confirm"),
    filters.PLFilter({"button": "confirm"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _send_call(ans: bots.SimpleBotEvent):
    admin_id = students.get_system_id_of_student(ans.object.object.message.peer_id)

    mention_storage = managers.MentionStorageManager(admin_id)

    msg = call.generate_message(admin_id)
    bits = 64
    await api_context.messages.send(
        peer_id=mention_storage.get_active_chat().chat_id,
        message=msg,
        random_id=random.getrandbits(bits),
        attachment=mention_storage.get_attaches() or "",
    )
    # TODO: очистка хранилища Призыва
    await ans.answer(
        "Сообщение отправлено",
        keyboard=kbs.main.main_menu(admin_id),
    )


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.StateFilter("mention_confirm"),
    filters.PLFilter({"button": "names_usage"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _invert_names_usage(ans: bots.SimpleBotEvent):
    admin_storage = managers.AdminConfigManager(
        students.get_system_id_of_student(ans.object.object.message.from_id),
    )
    admin_storage.invert_names_usage()
    await _confirm_call(ans)


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.StateFilter("mention_confirm"),
    filters.PLFilter({"button": "chat_config"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _select_chat(ans: bots.SimpleBotEvent):
    kb = await kbs.common.list_of_chats(
        students.get_system_id_of_student(ans.object.object.message.from_id),
    )
    await ans.answer("Выберите чат", keyboard=kb.get_keyboard())


@bots.simple_bot_message_handler(
    call_menu_router,
    filters.StateFilter("mention_confirm"),
    filters.PLFilter({"button": "chat"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _change_chat(ans: bots.SimpleBotEvent):
    payload = ujson.loads(ans.object.object.message.payload)
    admin_storage = managers.AdminConfigManager(
        students.get_system_id_of_student(ans.object.object.message.from_id),
    )
    admin_storage.update(
        active_chat=payload["chat_id"],
    )
    await _confirm_call(ans)
