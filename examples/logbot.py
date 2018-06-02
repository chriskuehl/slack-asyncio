"""A Slack bot that logs messages.

Watches for messages and prints them out, like so:

    [#ckuehl-test] <ckuehl> hello, world!
    [#rebuild] <jvperrin> Welp, guess that's not it
"""
import asyncio
import os

from slack_asyncio import bot


class LogBot(bot.SlackBot):

    userid_cache = {}
    channelid_cache = {}

    async def run_bot(self):
        self.register_handler('message', self.message_handler)

    async def user_id_to_user_name(self, userid):
        if userid not in self.userid_cache:
            user_info = await self.user_api.user_info(userid)
            self.userid_cache[userid] = user_info['user']['name']
        return self.userid_cache[userid]

    async def channel_id_to_channel_name(self, channelid):
        if channelid not in self.channelid_cache:
            channel_info = await self.user_api.channel_info(channelid)
            self.channelid_cache[channelid] = channel_info['channel']['name']
        return self.channelid_cache[channelid]

    async def message_handler(self, msg):
        if 'text' in msg:
            username = await self.user_id_to_user_name(msg['user'])
            channelname = await self.channel_id_to_channel_name(msg['channel'])
            print(f'[#{channelname}] <{username}> {msg["text"]}')


def main(argv=None):
    loop = asyncio.get_event_loop()
    bot = LogBot(
        # This example is designed to use your personal legacy token (which
        # acts sort of like both a user and bot token), but will also work with
        # modern tokens, if you desire.
        user_token=os.environ['SLACK_TOKEN'],
        bot_token=os.environ['SLACK_TOKEN'],
    )
    loop.run_until_complete(bot.run(loop))


if __name__ == '__main__':
    exit(main())
