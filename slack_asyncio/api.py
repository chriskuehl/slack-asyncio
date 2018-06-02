import contextlib
import urllib.parse


SLACK_API = 'https://slack.com/api'


def api_url(path, get_params=None):
    assert path.startswith('/'), path
    full_path = SLACK_API + path
    if get_params is not None:
        full_path += '?' + urllib.parse.urlencode(get_params)
    return full_path


class SlackAPI:
    """A client for the Slack HTTP API."""

    def __init__(self, *, user_token):
        self._user_token = user_token
        self._aiohttp_session = None

    @contextlib.contextmanager
    def configure_aiohttp_session(self, aiohttp_session):
        self._aiohttp_session = aiohttp_session
        try:
            yield
        finally:
            self._aiohttp_session = None

    async def leave_channel(self, channel):
        resp = await self._aiohttp_session.post(
            api_url(
                '/channels.leave',
                {'token': self._user_token, 'channel': channel},
            ),
        )
        resp.raise_for_status()

    async def user_info(self, user_id):
        resp = await self._aiohttp_session.get(
            api_url(
                '/users.info',
                {'token': self._user_token, 'user': user_id},
            ),
        )
        resp.raise_for_status()
        return await resp.json()

    async def channel_info(self, channel_id):
        resp = await self._aiohttp_session.get(
            api_url(
                '/channels.info',
                {'token': self._user_token, 'channel': channel_id},
            ),
        )
        resp.raise_for_status()
        return await resp.json()

    async def unfurl_link(self, *, channel, ts, unfurls):
        resp = await self._aiohttp_session.post(
            api_url('/chat.unfurl'),
            headers={'Authorization': f'Bearer {self._user_token}'},
            json={
                'channel': channel,
                'ts': ts,
                'unfurls': unfurls,
            },
        )
        resp.raise_for_status()
        return resp
