import pytest
from ethexporter import ContextMapping
from random import random
import logging
_log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_contextmapping_raises_key_error():
    m = ContextMapping(source={})
    with pytest.raises(KeyError):
        await m['xxx']


@pytest.mark.asyncio
async def test_contextmapping_caches_async_generator_once():
    async def _callable(context):
        for i in range(10):
            yield random() #mock.Mock(spec=) is broken on pytest-asyncio
    m = ContextMapping(source={'_callable1': _callable}, initial_keys=[])
    assert await m['_callable1'] == await m['_callable1']
    assert isinstance(await m['_callable1'], list)


@pytest.mark.asyncio
async def test_contextmapping_caches_awaitable_once():
    async def _callable(context):
        return random() #mock.Mock(spec=) is broken on pytest-asyncio
    m = ContextMapping(source={'_callable2': _callable}, initial_keys=[])
    assert await m['_callable2'] == await m['_callable2']
    assert isinstance(await m['_callable2'], float)


@pytest.mark.asyncio
async def test_contextmapping_caches_generator_once():
    def _callable(context):
        for i in range(10):
            yield random() #mock.Mock(spec=) is broken on pytest-asyncio
    m = ContextMapping(source={'_callable3': _callable}, initial_keys=[])
    assert await m['_callable3'] == await m['_callable3']
    assert isinstance(await m['_callable3'], list)


@pytest.mark.asyncio
async def test_contextmapping_caches_callable_once():
    def _callable(context):
        return random() #mock.Mock(spec=) is broken on pytest-asyncio
    m = ContextMapping(source={'_callable4': _callable}, initial_keys=[])
    assert await m['_callable4'] == await m['_callable4']
    assert isinstance(await m['_callable4'], float)


@pytest.mark.asyncio
async def test_contextmapping_len():
    assert len(ContextMapping(source={'a':'b'}, initial_keys=[])) == 1


@pytest.mark.asyncio
async def test_contextmapping_iter():
    assert list(ContextMapping(source={'a':'b'}, initial_keys=[])) == ['a',]