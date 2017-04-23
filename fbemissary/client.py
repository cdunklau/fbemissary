# Licensed under the Apache License:
#     http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/cdunklau/fbemissary/blob/master/NOTICE.txt
import urllib.parse
import logging


logger = logging.getLogger(__name__)


class PageMessagingAPIClient:
    def __init__(self, session, page_access_token):
        graph_api_version = 'v2.8'
        self._base_url = 'https://graph.facebook.com/{ver}/'.format(
            ver=graph_api_version)
        self._page_access_token = page_access_token
        self._session = session

    def _make_url(self, components):
        escaped_components = [urllib.parse.quote(c) for c in components]
        url = self._base_url + '/'.join(escaped_components)
        query = urllib.parse.urlencode({
            'access_token': self._page_access_token,
        })
        return '{url}?{query}'.format(url=url, query=query)

    async def send_message(self, recipient_id, message_payload):
        payload = {
            'recipient': {'id': recipient_id},
            'message': message_payload,
        }
        url = self._make_url(['me', 'messages'])
        async with self._session.post(url, json=payload) as response:
            structure = await response.json()
        return structure


class ConversationReplierAPIClient:
    def __init__(self, page_messaging_client, recipient_id):
        self._client = page_messaging_client
        self._recipient_id = recipient_id

    async def send_text_message(self, message_text):
        message_payload = {'text': message_text}
        structure = await self._client.send_message(
            self._recipient_id, message_payload)
        logger.debug(
            'Sent text message %r to ID %r, got API response %r',
            message_text, self._recipient_id, structure
        )
        return structure

    async def send_text_message_with_quickreplies(
            self, message_text, button_labels):
        quick_replies = [
            {'content_type': 'text', 'title': label, 'payload': label}
            for label in button_labels
        ]
        message_payload = {
            'text': message_text,
            'quick_replies': quick_replies,
        }
        structure = await self._client.send_message(
            self._recipient_id, message_payload)
        logger.debug(
            'Sent text message %r with buttons %r to ID %r, '
            'got API response %r',
            message_text, button_labels, self._recipient_id, structure)
        return structure
