from collections import defaultdict, Counter, namedtuple, OrderedDict
from functools import lru_cache, partial
import asyncio
import asyncio.base_futures
from itertools import chain, cycle
import logging
from pprint import pprint
import json
from web3 import Web3


_log = logging.getLogger(__name__)


NODE_LASTBLOCK = defaultdict(Counter)
# {<node>: {<acct_num>: <blocknum> }}



def _get_blockdata(node, blocknum):
    _log.debug('get', extra=locals())
    return asyncio.shield(asyncio.ensure_future(node.rpc_call('eth_getBlockByNumber', params=[hex(blocknum), True])))


def blockdata(node, blocknum):
    from ethexporter import config
    blockdata = config.block['data']
    if (not (node, blocknum) in blockdata) or blockdata[(node, blocknum)].cancelled():
        blockdata[(node, blocknum)] = _get_blockdata(node, blocknum)
    try:
        if blockdata[(node, blocknum)].exception():
            blockdata[(node, blocknum)] = _get_blockdata(node, blocknum)
    except asyncio.base_futures.InvalidStateError:
        pass
    return blockdata[(node, blocknum)]


async def get_token_contract_name(node, account):
    name = Web3.toText(await node.eth_call(None, data='0x06fdde03', to=hex(account)))
    return "".join(c for c in name if c.isprintable() or c in "\n\t").strip()


@lru_cache(maxsize=1024)
def token_contract(node, account):
    _log.debug('get', extra=locals())
    return asyncio.ensure_future(get_token_contract_name(node, account))

def gather_block_on_nodes(blocknum, nodes):
    return asyncio.shield(asyncio.gather(*(blockdata(node, blocknum) for node in nodes)))

def bursting(blockrange, size):
    _cycle = cycle(range(0, size))
    counter = next(_cycle)
    for blocknum, node_accounts in blockrange.items():
        blocks = None
        if counter == 0:
            subblockrange = list(range(blocknum, (blocknum - size) if (blocknum - size) in blockrange else list(blockrange)[-1], -1))
            _log.debug('bursting', extra={'blocks': subblockrange, 'nodes': list(node_accounts)})
            for _blocknum, _node_accounts in blockrange.items():
                if _blocknum in subblockrange:
                    blocks = gather_block_on_nodes(_blocknum, list(_node_accounts))
        yield blocks
        counter = next(_cycle)



async def iter_account_most_recent_tx(blockrange, direction):
    from ethexporter import config
    nodes = []

    burst = bursting(blockrange, config.scrape['burst'])
    for blocknum, node_accounts in blockrange.items():
        if not any([acct for acct in (acct_labels for acct_labels in node_accounts.values())]):
            break        
        nodes = list(node_accounts)
        next(burst)
        blocks = await gather_block_on_nodes(blocknum, nodes)
        for block, node in zip(blocks, nodes):
            for transaction in block['transactions']:
                for account, labels in list(node_accounts[node].items()):
                    if transaction[direction] == labels['account']:
                        yield node, blocknum, account, labels
                        del node_accounts[node][account]
    for node in nodes:
        NODE_LASTBLOCK[node][direction] = list(blockrange)[0]


async def get_blockrange_per_node(context, direction):
    # OrderedDict{<blocknum>:{<node_client>:{<acct_num>: labels}}}
    from ethexporter import config
    SCRAPE_MAXBLOCKS = config.scrape['maxblocks']

    accounts = []
    async for tx_settings in context['transaction']:
        accounts.extend(tx_settings.get(direction, []))

    nodes = [node async for node in context['nodes']]
    lastblocks = [lastblock async for lastblock in context['eth_lastblock_number']]
    node_lastblocks = list(zip(nodes, lastblocks))

    blockrange = OrderedDict()

    for node, lastblock in node_lastblocks:
        account_labels = {}
        client = node.value
        for account in accounts:
            if not account in account_labels:
                account_labels[account] = dict(account=hex(account), **node.labels)

            last_scraped_block = NODE_LASTBLOCK[client].get(direction, lastblock.value - SCRAPE_MAXBLOCKS)
            minblock = last_scraped_block if \
                        (lastblock.value - last_scraped_block) < SCRAPE_MAXBLOCKS \
                        else lastblock.value - SCRAPE_MAXBLOCKS
            
            for blocknum in range(lastblock.value, minblock, -1):
                if blocknum not in blockrange:
                    blockrange[blocknum] = {}
                if client not in blockrange[blocknum]:
                    blockrange[blocknum][client] = {}

                blockrange[blocknum][client] = account_labels
    return blockrange


async def most_recent_block_number(context):
    for direction in [tx_settings async for tx_settings in context['transaction']][0]:
        async for node, blocknum, account, labels in iter_account_most_recent_tx(await get_blockrange_per_node(context, direction), direction):
            contract_name = await asyncio.shield(token_contract(node, account))
            if not contract_name:
                contract_name = hex(account)
            yield blocknum, dict(direction=direction, token_contract_name=contract_name, **labels)

