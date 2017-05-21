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
    def __init__(
            self, messenger_client, conversationalist_factory_map,
            *, loop):
        self._conversationalist_factory_map = conversationalist_factory_map
        # Map of (page_id, counterpart_id) -> conversation
        self._convos = {}
        self._client = messenger_client
        self._loop = loop

    def add_messaging_events(self, page_id, events):
        for event in events:
            convo = self._get_or_create_conversation(page_id, event.sender_id)
            convo.add_messaging_event(event)

    def _get_or_create_conversation(self, page_id, counterpart_id):
        try:
            convo = self._convos[page_id, counterpart_id]
        except KeyError:
            replier = client.ConversationReplierAPIClient(
                self._client, counterpart_id)
            try:
                factory = self._conversationalist_factory_map[page_id]
            except KeyError:
                convo = UnhandledConversation(
                    None, page_id, counterpart_id, loop=self._loop)
            else:
                conversationalist = factory(
                    replier, page_id, counterpart_id, self._loop)
                convo = Conversation(
                    conversationalist, page_id, counterpart_id,
                    loop=self._loop)
            self._convos[page_id, counterpart_id] = convo
        return convo


class Conversation:
    """
    A chat with a single user.
    """
    def __init__(self, conversationalist, page_id, counterpart_id, *, loop):
        self._conversationalist = conversationalist
        self._page_id = page_id
        self._counterpart_id = counterpart_id
        self._loop = loop

    def add_messaging_event(self, event):
        try:
            self._conversationalist.handle_messaging_event(event)
        except Exception:
            logger.exception(
                'Error in handle_messaging_event for conversation '
                'on page %r with counterpart %r:',
                self._counterpart_id)


class UnhandledConversation(Conversation):
    def add_messaging_event(self, event):
        logger.warning(
            'Ignoring event received for page ID %r that has no '
            'conversationalist factory defined',
            self._page_id
        )


class SerialConversationalist:
    """
    A conversationalist implementation that queues messaging events
    and handles them serially.

    Subclass and implement the event_received coroutine method.

    ``event_received`` will be called with the event, and awaited.

    Attributes:
        replier (:class:`fbemissary.client.PageMessagingAPIClient`):
            The page messaging API client to use for sending
            messages etc. to the user.
        page_id (str):
            The Facebook Page ID.
        counterpart_id (str):
            The "Page-Scoped ID" of the user on the other end of the
            conversation.
        loop (:class:`asyncio.AbstractEventLoop`):
            The event loop instance.
    """
    def __init__(self, page_messaging_client, page_id, counterpart_id, loop):
        self.replier = page_messaging_client
        self.page_id = page_id
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
                    'Error in conversationalist method event_received '
                    'on page %r with counterpart %r:',
                    self.page_id, self.counterpart_id)
