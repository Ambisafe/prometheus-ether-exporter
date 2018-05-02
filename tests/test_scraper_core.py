import pytest




from web3.utils.datastructures import (
    AttributeDict,
)


@pytest.mark.asyncio
async def test_some_asyncio_code():
    from ethexporter import context
    await context.initial()
    from pprint import pprint
    v = await context['lastblock']
    print(v)
    pprint(AttributeDict.recursive(v[0].value))
