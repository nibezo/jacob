"""Главное меню бота."""

import os

from loguru import logger
from vkwave import api, bots, client

from jacob.database.utils import students
from jacob.database.utils.storages import managers
from jacob.services import keyboard as kbs
from jacob.services.exceptions import StudentNotFound
from jacob.services.filters import PLFilter
from jacob.services.logger.config import config

main_router = bots.DefaultRouter()
api_session = api.API(
    tokens=os.getenv("VK_CANARY_TOKEN"),
    clients=client.AIOHTTPClient(),
)
api_context = api_session.get_context()
logger.configure(**config)


@bots.simple_bot_message_handler(
    main_router,
    bots.TextFilter(["старт", "начать", "start", "привет", "hi", "hello"])
    | PLFilter({"button": "main_menu"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _greeting(ans: bots.SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        try:
            student_id = students.get_system_id_of_student(
                ans.object.object.message.peer_id,
            )
        except StudentNotFound:
            await ans.answer(
                "Вы не являетесь зарегистрированным студентом.\n"
                + "Желаете попасть в существующую группу или создать свою?",
                keyboard=kbs.main.choose_register_way(),
            )
        else:
            state_store = managers.StateStorageManager(student_id)
            state_store.update(state=state_store.get_id_of_state("main"))
            await ans.answer(
                "Привет!",
                keyboard=kbs.main.main_menu(
                    student_id,
                ),
            )


@bots.simple_bot_message_handler(
    main_router,
    PLFilter({"button": "create_new_group"}),
    bots.MessageFromConversationTypeFilter("from_pm"),
)
async def _show_universities(ans: bots.SimpleBotEvent):
    with logger.contextualize(user_id=ans.object.object.message.from_id):
        # режим: выбор универа
        await ans.answer(
            "Выбери университет",
            keyboard=kbs.main.universities(),
        )
