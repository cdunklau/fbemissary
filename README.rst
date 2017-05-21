.. image:: https://img.shields.io/pypi/v/fbemissary.svg
    :target: https://pypi.python.org/pypi/fbemissary

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
    import collections

    import aiohttp.web

    import fbemissary


    logger = logging.getLogger(__name__)


    class EchoConversationalist(fbemissary.SerialConversationalist):
        async def event_received(self, event):
            if (
                    isinstance(event, fbemissary.ReceivedMessage)
                    and event.text is not None
                ):
                logger.debug(
                    'Echoing message back to %r',
                    self.counterpart_id)
                await self.replier.send_text_message(event.text)
            else:
                logger.warning('Ignoring event {0}'.format(event))


    async def start(loop):
        fbmessenger = fbemissary.FacebookPageMessengerBot(
            app_secret='<APP_SECRET>',
            verify_token='<WEBHOOK_VERIFY_TOKEN>')
        fbmessenger.add_conversationalist_factory(
            page_id='<PAGE_ID>', 
            page_access_token='<PAGE_ACCESS_TOKEN>',
            conversationalist_factory=EchoConversationalist)
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
