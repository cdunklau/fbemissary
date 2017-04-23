fbemissary
##########

A bot framework for the Facebook Messenger platform,
built on asyncio and aiohttp.

Still very rough.


Example Usage
=============

.. code:: python

    import sys
    import asyncio
    import logging

    import aiohttp.web

    import fbemissary


    logger = logging.getLogger(__name__)


    class EchoConversationalist:
        def __init__(self, replier, counterpart_id):
            self._replier = replier
            self._counterpart_id = counterpart_id

        async def handle_messaging_event(self, event):
            if (
                    isinstance(event, fbemissary.ReceivedMessage)
                    and event.text is not None
                ):
                logger.debug(
                    'Echoing message back to %r',
                    self._counterpart_id)
                await self._replier.send_text_message(event.text)
            else:
                logger.warning('Ignoring event {0}'.format(event))


    async def start(loop):
        fbconfig = fbemissary.FacebookMessengerBotConfig(
            app_id='<APP_ID>',
            app_secret='<APP_SECRET>',
            verify_token='<WEBHOOK_VERIFY_TOKEN>',
            page_access_token='<PAGE_ACCESS_TOKEN>',
        )
        fbmessenger = fbemissary.FacebookPageMessengerBot(
            fbconfig, EchoConversationalist)
        webapp = aiohttp.web.Application()
        await fbmessenger.start(
            '/webhooks/facebook-messenger',
            webapp.router,
            loop=loop
        )
        server_port = 8080
        server_interface = 'localhost'
        webhandler = webapp.make_handler(loop=loop)
        webserver = await loop.create_server(
            webhandler,
            server_interface,
            server_port,
        )


    def main():
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
        loop = asyncio.get_event_loop()
        loop.create_task(start(loop))
        loop.run_forever()

    if __name__ == '__main__':
        main()
