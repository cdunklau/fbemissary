# Licensed under the Apache License:
#     http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/cdunklau/fbemissary/blob/master/NOTICE.txt
import logging
import hmac

import aiohttp.web

from fbemissary import models


logger = logging.getLogger(__name__)


class WebhookReceiver:
    """
    Receive Facebook webhooks and dispatch the received structure to
    the ``webhook_structure_handler``.
    """
    def __init__(self, app_secret, verify_token, webhook_structure_handler,
                 *, loop):
        self._loop = loop
        self._app_secret = app_secret
        self._verify_token = verify_token
        self._handler = webhook_structure_handler

    def setup_routes(self, mountpoint, router):
        router.add_get(mountpoint, self.verify_subscription)
        router.add_post(mountpoint, self.receive_update)

    async def verify_subscription(self, request):
        mode = request.query.get('hub.mode')
        token = request.query.get('hub.verify_token')
        if mode == 'subscribe' and token == self._verify_token:
            logger.info(
                'Received correct verify token, replying with challenge')
            challenge = request.query.get('hub.challenge')
            return aiohttp.web.Response(text=challenge)
        else:
            fmt = (
                'Verify token does not match or unexpected request, '
                'query string was: %r'
            )
            logger.warning(fmt, request.query_string)
            return aiohttp.web.Response(status=403)

    async def receive_update(self, request):
        if not await self._has_valid_signature(request):
            logger.warning('Signature mismatch for webhook request')
            return aiohttp.web.Response(status=403)
        structure = await request.json()
        logger.debug('Received update %r', await request.read())
        self._handler.handle_webhook_structure(structure)
        return aiohttp.web.Response(status=200)

    async def _has_valid_signature(self, request):
        sig_header_value = request.headers.get('X-Hub-Signature', 'sha1=')
        _, _, signature = sig_header_value.partition('sha1=')
        content = await request.read()
        key = self._app_secret.encode('ascii')
        verifier = hmac.new(key, msg=content, digestmod='sha1')
        computed_signature = verifier.hexdigest()
        return signature == computed_signature


class WebhookWrangler:
    def __init__(self, messaging_events_received):
        self._object_handlers = {
            'page': self._handle_page_structure,
        }
        self._messaging_events_received = messaging_events_received

    def handle_webhook_structure(self, structure):
        try:
            objtype = structure['object']
        except KeyError:
            logger.warning(
                "No 'object' key in webhook structure %r", structure)
            return
        handler = self._object_handlers.get(objtype)
        if handler is None:
            logger.warning('No handler for webhook object type %r', objtype)
            return
        handler(structure)

    def _handle_page_structure(self, structure):
        assert structure['object'] == 'page'
        extra_keys = structure.keys() - {'object', 'entry'} 
        if extra_keys:
            logger.warning(
                'Unhandled keys in webhook structure: %r', extra_keys)
        try:
            entry_structures = structure['entry']
        except KeyError:
            logger.warning(
                "No 'entry' key in webhook structure: %r", structure)
            return
        logger.debug('Got %d page webhook entries', len(entry_structures))
        self._handle_page_entries(entry_structures)

    def _handle_page_entries(self, entry_structures):
        for entry in entry_structures:
            if 'messaging' not in entry:
                logger.warning('Ignoring non-messaging entry: %r', entry)
                continue
            event_structures = entry['messaging']
            logger.debug(
                'Processing %d messaging event structures',
                len(event_structures))
            events = []
            for event_structure in event_structures:
                try:
                    event = models.model_from_entry_structure(
                        event_structure)
                except Exception:  # FIXME: Too broad
                    logger.exception(
                        'Failed to parse event structure %r',
                        event_structure)
                else:
                    events.append(event)
            self._messaging_events_received(events)
