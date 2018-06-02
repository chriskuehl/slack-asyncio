from setuptools import find_packages
from setuptools import setup


setup(
    name='slack-asyncio',
    description='Slack bot and API library using asyncio',
    url='https://github.com/chriskuehl/slack-asyncio',
    version='0.0.0',

    author='Chris Kuehl',
    author_email='ckuehl@ckuehl.me',

    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],

    packages=find_packages(exclude=('tests*', 'testing*')),
    install_requires=[
        'aiohttp',
        'asyncio-extras',
        'websockets',
    ],
)
