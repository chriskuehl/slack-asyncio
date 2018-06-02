"""A Slack bot that can unfurl links.

In general, it's probably easier to set up an incoming webhook (on your end)
that Slack triggers when a matching URL is posted, and call the unfurl API from
that. There are some cases where a bot is nice, though:

    * It allows opt-in (each channel can /invite the bot if they want to)

    * It's hard to expose a webhook to the public internet (e.g. if the
      resource you're unfurling is in your dev environment, it might be easier
      to run a bot from dev, than accept webhooks and prod and figure out how
      to get them into dev where they can be unfurled).
"""
import asyncio
import os
import re

from slack_asyncio import bot


class UnfurlBot(bot.SlackBot):

    async def run_bot(self):
        self.register_handler('message', self.message_handler)

    async def message_handler(self, msg):
        for link in re.findall(
            r'<(https?://www.ocf.berkeley.edu/.*?)(?:\||>)',
            msg.get('text', ''),
        ):
            self.schedule(self.unfurl_link(
                link=link,
                channel=msg['channel'],
                ts=msg['ts'],
            ))

    async def unfurl_link(self, *, link, channel, ts):
        # This silly example just fetches the status code of the URL and uses
        # that as the unfurl.
        resp = await self.aiohttp_session.get(link)

        # This is where you'd want to produce something useful :)
        unfurl_text = f'That resource had status code: {resp.status}'

        await self.user_api.unfurl_link(
            channel=channel,
            ts=ts,
            unfurls={
                link: {
                    'footer': 'hello footer!',
                    'footer_icon': 'https://i.fluffy.cc/SScDmZnqsRnNGBwrPBF4MNKSdG8tqKsF.png',
                    'text': unfurl_text,
                },
            },
        )


def main(argv=None):
    loop = asyncio.get_event_loop()
    bot = UnfurlBot(
        # A user token is needed to call the unfurl API, and a bot token is
        # needed for the bot user.
        #
        # Unfortunately, a personal "legacy" token won't work for the unfurl
        # API.
        user_token=os.environ['SLACK_USER_TOKEN'],
        bot_token=os.environ['SLACK_BOT_TOKEN'],
    )
    loop.run_until_complete(bot.run(loop))


if __name__ == '__main__':
    exit(main())
