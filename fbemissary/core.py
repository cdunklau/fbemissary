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
    ``conversationalist_factory``
    Arguments:
        conversationalist_factory:
            A callable supporting three arguments which returns a
            "conversationalist" object. A conversationalist is an
            object that receives messaging events (described in the
            documentation for :mod:`fbemissary.models`) from a
            conversation with a single user and replies as needed.

            The interface is described below.

        app_secret (str):
            The Facebook "app secret". This is available after you
            set up your app, at https://developers.facebook.com/apps/
            on the dashboard.

        verify_token (str):
            The string you gave when you added the webhook
            subscription. Used by Facebook to verify your bot is
            actually yours.

        page_access_token (str):
            The access token for Facebook Page that your app is
            subscribed to.


    The argument ``conversationalist_factory`` will be called with
    three arguments: an instance of
    :class:`fbemissary.client.ConversationReplierAPIClient` (for
    sending messages back to the user), the page-scoped ID of the
    conversation counterpart (the user on the other end of the
    conversation), and the event loop.

    The factory must return an object with a
    ``handle_messaging_event`` method (not a coroutine!) that accepts
    a messaging event.

    .. todo::

        Add documentation for the included concrete implementations
        of conversationalist factories.
    """
    def __init__(
            self, conversationalist_factory,
            app_secret, verify_token, page_access_token):
        self._app_secret = app_secret
        self._verify_token = verify_token
        self._page_access_token = page_access_token
        self._conversationalist_factory = conversationalist_factory
        # These are overwritten in start()
        self._message_demuxer = None
        self._webhook_wrangler = None
        self._receiver = None
        self._sender = None

    async def start(self, webapp_mountpoint, webapp_router, *, loop):
        self._sender = client.PageMessagingAPIClient(
            aiohttp.ClientSession(),
            self._page_access_token,
        )
        self._message_demuxer = conversation.MessagingEventDemuxer(
            self._sender, self._conversationalist_factory, loop=loop)
        self._webhook_wrangler = webhook.WebhookWrangler(
            self._message_demuxer.add_messaging_events)
        self._receiver = webhook.WebhookReceiver(
            self._app_secret,
            self._verify_token,
            self._webhook_wrangler,
            loop=loop,
        )
        self._receiver.setup_routes(webapp_mountpoint, webapp_router)
