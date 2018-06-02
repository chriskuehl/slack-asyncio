import asyncio
import collections
import functools
import json
import time

import aiohttp
import asyncio_extras.contextmanager
import websockets

from slack_asyncio import api


def _require_connected(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        assert self.connected is True, 'Bot must be connected to call this method!'
        return fn(self, *args, **kwargs)
    return wrapper


class BaseSlackBot:
    """A Slack bot that connects to the RTM API and nothing more."""

    def __init__(self, *, bot_token):
        self._bot_token = bot_token
        self._reset_state()

    def _reset_state(self):
        self.connected = False
        self.aiohttp_session = None
        self._ws = None
        self._msgid = 1

    @asyncio_extras.contextmanager.async_contextmanager
    async def connect(self):
        assert not self.connected

        try:
            async with aiohttp.ClientSession() as self.aiohttp_session:
                # Get the websocket URL
                resp = await self.aiohttp_session.get(
                    api.api_url('/rtm.connect', {'token': self._bot_token}),
                )
                resp.raise_for_status()
                json = await resp.json()

                async with websockets.connect(json['url']) as self._ws:
                    self.connected = True
                    yield
        finally:
            self._reset_state()

    # Bot RTM methods. These require the bot to be connected to work.
    @_require_connected
    async def send_rtm_message(self, msg):
        msg['msgid'] = self._msgid
        self.schedule(self._ws.send(json.dumps(msg)))
        self._msgid += 1

    # Bot API methods. These don't use the RTM API or require the bot to be
    # connected to work, but they do use the bot token (rather than the user token).
    async def all_channels(self):
        args = {'token': self._bot_token, 'limit': 200, 'exclude_members': True}
        # cursor turns to empty string at the end
        while 'cursor' not in args or args['cursor'] != '':
            resp = await self.aiohttp_session.get(
                api.api_url('/channels.list', args),
            )
            resp.raise_for_status()
            j = await resp.json()
            assert j['ok'] is True
            # There's no async "yield from" :(
            for channel in j['channels']:
                yield channel

            args['cursor'] = j['response_metadata']['next_cursor']

    async def my_public_channels(self):
        async for channel in self.all_channels():
            if channel['is_member']:
                yield channel['name']

    async def send_message(self, *, channel, text):
        resp = await self.aiohttp_session.post(
            api.api_url('/chat.postMessage'),
            headers={
                'Authorization': f'Bearer {self._bot_token}',
            },
            json={
                'channel': channel,
                'text': text,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def identity(self):
        resp = await self.aiohttp_session.get(
            api.api_url('/auth.test', {'token': self._bot_token}),
        )
        resp.raise_for_status()
        return await resp.json()


class SlackBot(BaseSlackBot):
    """A useful Slack bot base class that tries to do sane things.

    It includes a scheduling interface and some useful features like automatic
    disconnects.
    """

    _disconnect_timeout = 5

    def __init__(self, *, user_token, bot_token):
        super().__init__(bot_token=bot_token)
        self.user_api = api.SlackAPI(user_token=user_token)
        self._reset_state()

    def _reset_state(self):
        super()._reset_state()
        self._working = False
        self._tasks = set()
        self._message_handlers = collections.defaultdict(set)

    async def run(self, loop):
        """Run the bot forever with default scheduling.

        Example usage:

            loop = asyncio.get_event_loop()
            loop.run_until_completion(bot.run(loop))
        """
        async with self.connect():
            with self.user_api.configure_aiohttp_session(self.aiohttp_session):
                self._loop = loop

                self.schedule(self._disconnect_loop())
                self.schedule(self._receive_loop())
                self.schedule(self.run_bot())

                while len(self._tasks) > 0:
                    finished = {task for task in self._tasks if task.done()}
                    self._tasks -= finished
                    for task in finished:
                        task.result()
                    await asyncio.sleep(0.1)

    async def run_bot(self):
        """Run the bot's logic!

        Override this in your bot class.
        """
        raise NotImplementedError('Implement me in your subclass!')

    @_require_connected
    def schedule(self, awaitable):
        self._tasks.add(self._loop.create_task(awaitable))

    @_require_connected
    def register_handler(self, type_, handler):
        self._message_handlers[type_].add(handler)

    @_require_connected
    async def _disconnect_loop(self):
        # TODO: consider reconnecting instead of killing the bot entirely on timeout
        async def pong_handler(msg):
            self._last_pong = time.time()

        self._last_pong = time.time()
        self.register_handler('pong', pong_handler)
        while True:
            elapsed = time.time() - self._last_pong
            if elapsed > self._disconnect_timeout:
                raise TimeoutError(f'No pong received from Slack within {elapsed} seconds.')

            await self.send_rtm_message({'type': 'ping'})
            await asyncio.sleep(1)

    @_require_connected
    async def _receive_loop(self):
        while True:
            msg = json.loads(await self._ws.recv())
            type_ = msg.get('type')

            for handler in self._message_handlers[type_]:
                self.schedule(handler(msg))
