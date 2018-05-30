
import asyncio
import logging
_log = logging.getLogger(__name__)

async def convert_lastblock_number(rpc_call):
    return int((await rpc_call), 16)

async def lastblock_number(context):
    async for node in context['nodes']:
        yield asyncio.ensure_future(convert_lastblock_number(node.value.rpc_call('eth_blockNumber'))), node.labels
