# Licensed under the Apache License:
#     http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/cdunklau/fbemissary/blob/master/NOTICE.txt
import logging
import collections
import asyncio

from fbemissary import models
from fbemissary import client


logger = logging.getLogger(__name__)


class MessagingEventDemuxer:
    """
    Split messaging events based on the sender's ID and give them
    to :class:`Conversation` instances.
    """
    def __init__(self, messenger_client, conversationalist_factory, *, loop):
        self._conversationalist_factory = conversationalist_factory
        self._convos = {}
        self._client = messenger_client
        self._loop = loop

    def add_messaging_events(self, events):
        for event in events:
            convo = self._get_or_create_conversation(event.sender_id)
            convo.add_messaging_event(event)

    def _get_or_create_conversation(self, counterpart_id):
        try:
            convo = self._convos[counterpart_id]
        except KeyError:
            replier = client.ConversationReplierAPIClient(
                self._client, counterpart_id)
            conversationalist = self._conversationalist_factory(
                replier, counterpart_id)
            convo = Conversation(
                conversationalist, counterpart_id, loop=self._loop)
            self._convos[counterpart_id] = convo
        return convo


class Conversation:
    """
    A chat with a single user.
    """
    def __init__(self, conversationalist, counterpart_id, *, loop):
        self._conversationalist = conversationalist
        self._counterpart_id = counterpart_id
        self._events = collections.deque()
        self._loop = loop
        self._events_available = asyncio.Event(loop=loop)
        self._task = loop.create_task(self._conversate())

    def add_messaging_event(self, event):
        # Load the event...
        self._events.appendleft(event)
        # ...and inform the task it can continue.
        logger.debug(
            'Notifying myself that event is available for %r',
            self._counterpart_id)
        self._events_available.set()

    async def _conversate(self):
        logger.info('Started conversation with ID %r', self._counterpart_id)
        while True:
            await self._handle_events()
            self._events_available.clear()
            await self._events_available.wait()


    async def _handle_events(self):
        while self._events:
            event = self._events.pop()
            try:
                await self._conversationalist.handle_messaging_event(event)
            except Exception:
                logger.exception(
                    'Error in conversation with %r',
                    self._counterpart_id)
