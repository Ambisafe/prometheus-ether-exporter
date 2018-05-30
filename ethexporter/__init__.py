import devconfig
devconfig.merges['ethexporter_config']._with('ethexporter_config', 'ethexporter.defaults')

try:
    import ethexporter_config as config
except ModuleNotFoundError:
    import ethexporter.defaults as config

import inspect
import logging
from collections import namedtuple
import collections.abc
from functools import lru_cache
import asyncio
import devconfig.mapping

from ethexporter import config
_log = logging.getLogger(__name__)

LabeledValue = namedtuple('Labeled', ('value', 'labels'))


_ctx_source = devconfig.mapping.merge(
                dict((name, metric['scraper']) for name, metric in getattr(config, 'metrics', {}).items()),
                getattr(config, 'scrapers', {}),
                getattr(config, 'initial', {}))


class ContextMapping(collections.abc.Mapping):
    def __init__(self, source=_ctx_source, initial_keys=getattr(config, 'initial', {}).keys()):
        self._source = source
        self._data = {}
        self._log = logging.getLogger(__name__ + '.context')
        self.initial_keys = initial_keys

    async def initial(self):
        for k in self.initial_keys:
            async for v in self[k]:
                pass

    def __iter__(self):
        yield from self._source

    def __len__(self):
        return len(self._source)

    @classmethod
    @lru_cache(maxsize=1024)
    def cachelock(cls, name):
        return asyncio.Lock()

    async def iterscraper(self, scraper, logdata):
        if inspect.isasyncgenfunction(scraper):
            items = []
            self._log.debug(f'scraping {logdata["key"]!r} key with async for', extra=logdata)
            try:
                async for item in scraper(self):
                    yield item
            except ConnectionError as e:
                _log.exception(e)
        elif inspect.iscoroutinefunction(scraper):
            self._log.debug(f'scraping {logdata["key"]!r} key with await', extra=logdata)
            try:
                yield (await scraper(self))
            except ConnectionError as e:
                _log.exception(e)
        elif inspect.isgeneratorfunction(scraper):
            self._log.debug(f'scraping {logdata["key"]!r} key with list', extra=logdata)
            try:
                for item in scraper(self):
                    yield item
            except ConnectionError as e:
                _log.exception(e)
        elif inspect.isfunction(scraper):
            self._log.debug(f'scraping {logdata["key"]!r} key with call', extra=logdata)
            try:
                yield scraper(self)
            except ConnectionError as e:
                _log.exception(e)
        else:
            self._log.debug(f'scraping {logdata["key"]!r} key as value', extra=logdata)
            yield scraper

    async def __getitem__(self, name):
        if name not in self._source:
            raise KeyError(name)
        await self.cachelock(name)
        try:
            if name not in self._data:
                self._data[name] = []
                logdata = {'context': self, 'key': name}
                scraper = self._source[name]
                items = []
                async for item in self.iterscraper(scraper, logdata):
                    if isinstance(item, tuple) and len(item) == 2:
                        item = LabeledValue(*item)
                    items.append(item)

                await asyncio.gather(*[item.value for item in items if isinstance(item, LabeledValue) and isinstance(item.value, asyncio.Future)])

                for item in items:
                    if isinstance(item, LabeledValue) and isinstance(item.value, asyncio.Future):
                        item = LabeledValue(item.value.result(), item.labels)
                    self._data[name].append(item)
                    yield item
            else:
                for item in self._data[name]:
                    yield item
        except Exception as e:
            _log.exception(e)
            if name in self._data:
                del self._data[name]
        finally:
            self.cachelock(name).release()

    async def reset(self):
        for k in self:
            if k not in self.initial_keys and k in self._data:
                _log.debug(f'removing non initial {k!r}')
                async with self.cachelock(k):
                    if k in self._data:
                        del self._data[k]


context = ContextMapping()