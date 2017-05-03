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
                self._conversationalist.handle_messaging_event(event)
            except Exception:
                logger.exception(
                    'Error in handle_messaging_event for conversation '
                    'with %r',
                    self._counterpart_id)


class SerialConversationalist:
    """
    A conversationalist implementation that queues messaging events
    and handles them serially.

    Subclass and implement the event_received coroutine method.

    ``event_received`` will be called with the event, and awaited.

    Attributes:
        replier (:class:`fbemissary.PageMessagingAPIClient`):
            The page messaging API client to use for sending
            messages etc. to the user.
        counterpart_id (str):
            The "Page-Scoped ID" of the user on the other end of the
            conversation.
        loop (:class:`asyncio.AbstractEventLoop`):
            The event loop instance.
    """
    def __init__(self, page_messaging_client, counterpart_id, loop):
        self.replier = page_messaging_client
        self.counterpart_id = counterpart_id
        self.loop = loop
        self._events = collections.deque()
        self._events_available = asyncio.Event(loop=loop)
        self._task = loop.create_task(self._conversate())

    async def event_received(self, event):
        """
        Abstract coroutine method.
        """
        pass

    def handle_messaging_event(self, event):
        # Load the event...
        self._events.appendleft(event)
        # ...and inform the task it can continue.
        self._events_available.set()

    async def _conversate(self):
        while True:
            await self._handle_events()
            self._events_available.clear()
            await self._events_available.wait()


    async def _handle_events(self):
        while self._events:
            event = self._events.pop()
            try:
                await self.event_received(event)
            except Exception:
                logger.exception(
                    'Error in conversationalist event_received with %r',
                    self._counterpart_id)
