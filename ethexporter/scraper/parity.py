import logging
_log = logging.getLogger(__name__)
from collections import Counter, defaultdict
from copy import copy
import asyncio

async def local_transactions(context):
    async for node in context['nodes']:
        yield asyncio.ensure_future(node.value.rpc_call('parity_localTransactions')), node.labels


def transaction_labels(node_local_transactions):
    transactions_labels = tuple((k,v) for (k,v) in node_local_transactions.labels.items())
    for transaction in node_local_transactions.value.values():
        if transaction['status'] in ('future', 'pending'):
            labels = copy(transactions_labels)
            yield labels + (('local_transaction_status', transaction['status']),)



async def local_transactions_total(context):
    counter = Counter()
    async for local_transactions in context['local_transactions']:
        for labels in transaction_labels(local_transactions):
            counter[labels] += 1
        for labels, value in counter.items():
            yield value, dict(labels)
