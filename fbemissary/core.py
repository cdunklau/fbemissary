# Licensed under the Apache License:
#     http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/cdunklau/fbemissary/blob/master/NOTICE.txt
import logging

import aiohttp
import attr

from fbemissary import conversation
from fbemissary import webhook
from fbemissary import client


logger = logging.getLogger(__name__)


class FacebookPageMessengerBot:
    """
    Arguments:
        app_secret (str):
            The Facebook "app secret". This is available after you
            set up your app, at https://developers.facebook.com/apps/
            on the dashboard.

        verify_token (str):
            The string you gave when you added the webhook
            subscription. Used by Facebook to verify your bot is
            actually yours.

    """
    def __init__(self, app_secret, verify_token):
        self._app_secret = app_secret
        self._verify_token = verify_token
        self._message_demuxer = conversation.MessagingEventDemuxer()
        # These are overwritten in start()
        self._webhook_wrangler = None
        self._receiver = None
        self._sender = None
        self._started = False

    def add_conversationalist_factory(
            self, page_id, page_access_token, conversationalist_factory):
        """
        Arguments:
            page_id (str):
                The ID for a Facebook Page that your app is subscribed
                to, which the ``conversationalist_factory`` will handle
            page_access_token (str):
                The access token for the Facebook Page specified by
                the ``page_id``
            conversationalist_factory:
                A Conversationalist Factory is a callable supporting
                four arguments which returns a "Conversationalist"
                object. The interfaces are described below.

        Conversationalist Factories will be called with four arguments:
        an instance of
        :class:`fbemissary.client.ConversationReplierAPIClient` (for
        sending messages back to the user), the Facebook Page ID,
        the page-scoped ID of the conversation counterpart (the user on
        the other end of the conversation), and the event loop.

        The factory must return a Conversationalist object: an
        object with a ``handle_messaging_event`` method
        (not a coroutine!) that accepts a messaging event.

        A Conversationalist is an object that receives messaging
        events (described in the documentation for
        :mod:`fbemissary.models`) from a conversation with a single
        user and replies as needed.

        .. todo::

            Add documentation for the included concrete implementations
            of conversationalist factories.
        """
        if self._started:
            # TODO: Change this to a custom exception
            raise RuntimeError('Cannot change config after start')
        self._message_demuxer.add_conversationalist_factory(
            page_id, page_access_token, conversationalist_factory)

    async def start(self, webapp_mountpoint, webapp_router, *, loop):
        if self._started:
            # TODO: Change this to a custom exception
            raise RuntimeError('Cannot start more than once')
        self._session = aiohttp.ClientSession()
        self._message_demuxer.start(self._session, loop=loop)
        self._webhook_wrangler = webhook.WebhookWrangler(
            self._message_demuxer.add_messaging_events)
        self._receiver = webhook.WebhookReceiver(
            self._app_secret,
            self._verify_token,
            self._webhook_wrangler,
            loop=loop,
        )
        self._receiver.setup_routes(webapp_mountpoint, webapp_router)
        self._started = True
