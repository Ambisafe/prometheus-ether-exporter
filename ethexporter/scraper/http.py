
import asyncio
import logging
from aiohttp.client import ClientSession
import ujson
_log = logging.getLogger(__name__)

async def convert_lastblock_number(response):
    return int((await response)['result'], 16)

async def etherscan_lastblock_number(context):
    from ethexporter import config
    url = config.metrics['etherscan_lastblock_number']['options']['etherscan_url']
    async with ClientSession() as client:
            response =  await client.get(
                url=url,
            )
            if response.status == 200:
                yield asyncio.ensure_future(convert_lastblock_number(response.json(loads=ujson.loads))), {'source': url}
