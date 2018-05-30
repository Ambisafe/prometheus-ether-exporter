from functools import lru_cache
import logging
from aioethereum import AsyncIOHTTPClient
from aioethereum.errors import BadJsonError, BadResponseError
from aiohttp.client import ClientSession
import asyncio
import async_timeout
import ujson
from urllib.parse import urlparse



_log = logging.getLogger(__name__)

class AsyncioWEB3RPCClient(AsyncIOHTTPClient):

    async def rpc_call(self, method, params=None, id_=None):
        params = params or []
        data = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': id_ or self._id,
        }
        async with ClientSession(loop=self._loop) as client:
            async with async_timeout.timeout(self._timeout, loop=self._loop):
                response =  await client.post(
                    url=self._endpoint,
                    data=ujson.dumps(data),
                    headers={'Content-Type': 'application/json'}
                )
                _log.debug('sent', extra={'response':response, 'data': data})
                if response.status != 200:
                    raise BadStatusError(response.status)

                if id_ is None:
                    self._id += 1
                try:
                    data = await response.json(loads=ujson.loads)
                except ValueError:
                    raise BadJsonError('Invalid jsonrpc response')
                if 'result' not in data and 'error' in data:
                    raise BadResponseError( data['error']['message'],
                                            data['error']['code'])
                elif 'result' not in data:
                    raise KeyError('result')
                else:
                    return data['result']


async def create_ethereum_client(uri, timeout=60, *, loop=None):
    """Create client to ethereum node based on schema.

    :param uri: Host on ethereum node
    :type uri: str

    :param timeout: An optional total time of timeout call
    :type timeout: int

    :param loop: An optional *event loop* instance
                 (uses :func:`asyncio.get_event_loop` if not specified).
    :type loop: :ref:`EventLoop<asyncio-event-loop>`

    :return: :class:`BaseAsyncIOClient` instance.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    presult = urlparse(uri)
    if presult.scheme in ('ipc', 'unix'):
        reader, writer = await asyncio.open_unix_connection(presult.path,
                                                                 loop=loop)
        return AsyncIOIPCClient(reader, writer, uri, timeout, loop=loop)
    elif presult.scheme in ('http', 'https'):
        tls = presult.scheme[-1] == 's'
        netloc = presult.netloc.split(':')
        host = netloc.pop(0)
        port = netloc.pop(0) if netloc else (443 if tls else 80)
        return AsyncioWEB3RPCClient(host, port, tls, timeout, loop=loop)
    else:
        raise RuntimeError('This scheme does not supported.')


async def nodes(context):
    from ethexporter import LabeledValue as LV
    async for nodemap in context['urls']:
        for node, url in nodemap.items():

            yield LV(await create_ethereum_client(url), {'node': node, 'url': url})



