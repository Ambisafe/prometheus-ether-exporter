
import asyncio
import logging
from aiohttp.client import ClientSession
import ujson
_log = logging.getLogger(__name__)

async def convert_lastblock_number(response):
    return int((await response)['result'], 16)

async def etherscan_lastblock_number(context, url='https://api.etherscan.io/api?module=proxy&action=eth_blockNumber'):
    async with ClientSession() as client:
            response =  await client.get(
                url=url,
            )
            if response.status == 200:
                yield asyncio.ensure_future(convert_lastblock_number(response.json(loads=ujson.loads))), {'source': url}
