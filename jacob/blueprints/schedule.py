import os

from loguru import logger
from vkwave.api import API
from vkwave.bots import DefaultRouter
from vkwave.bots import MessageFromConversationTypeFilter
from vkwave.bots import SimpleBotEvent
from vkwave.bots import simple_bot_message_handler
from vkwave.client import AIOHTTPClient

from jacob.services import filters
from jacob.services.logger.config import config

schedule_router = DefaultRouter()
api_session = API(tokens=os.getenv("VK_TOKEN"), clients=AIOHTTPClient())
api = api_session.get_context()
logger.configure(**config)


@simple_bot_message_handler(
    schedule_router,
    filters.PLFilter({"button": "schedule"}),
    MessageFromConversationTypeFilter("from_pm"),
)
@logger.catch()
async def start_call(ans: SimpleBotEvent):
    await ans.answer("Этот раздел находится в разработке")
