from collections import defaultdict
import logging
from aioethereum import create_ethereum_client

_log = logging.getLogger(__name__)
async def nodes(context):
    from ethexporter import LabeledValue as LV
    for node, url in (await context['urls']).items():
        yield LV(await create_ethereum_client(url), {'node': node, 'url': url})


async def eth_lastblock_num(context):
    from ethexporter import LabeledValue as LV
    for node in await context['nodes']:
        try:
            yield LV(await node.value.eth_blockNumber(), node.labels)
        except ConnectionError as e:
            _log.exception(e)


async def lastblock(context):
    from ethexporter import LabeledValue as LV
    nodes = await context['nodes']
    lastblocks = await context['eth_lastblock_num']
    node_lastblocks = defaultdict(list)
    for node in nodes:
        for lastblock in lastblocks:
            if lastblock.labels['node'] == node.labels['node']:
                node_lastblocks[node.labels['node']].extend([node.value, lastblock.value, lastblock.labels])

    for name, (node, lastblock, labels) in node_lastblocks.items():
        try:
            yield LV(await node.eth_getBlockByNumber(lastblock), labels)
        except ConnectionError as e:
            _log.exception(e)

async def eth_lastblock_size(context):
    from ethexporter import LabeledValue as LV
    for lastblock in await context['lastblock']:
        yield LV(int(lastblock.value['size'], 0), lastblock.labels)


async def eth_gas_limit(context):
    from ethexporter import LabeledValue as LV
    for lastblock in await context['lastblock']:
        yield LV(int(lastblock.value['gasLimit'], 0), lastblock.labels)


async def eth_gas_used(context):
    from ethexporter import LabeledValue as LV
    for lastblock in await context['lastblock']:
        yield LV(int(lastblock.value['gasUsed'], 0), lastblock.labels)