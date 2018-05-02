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
        [await self[k] for k in self.initial_keys]

    def __iter__(self):
        yield from self._source

    def __len__(self):
        return len(self._source)

    async def __getitem__(self, name):
        if name not in self._source:
            raise KeyError(name)

        if name not in self._data:
            logdata = {'context': self, 'key': name}
            scraper = self._source[name]
            if inspect.isasyncgenfunction(scraper):
                items = []
                self._log.debug(f'caching {name!r} key with async for', extra=logdata)
                async for item in scraper(self):
                    items.append(item)
            elif inspect.iscoroutinefunction(scraper):
                self._log.debug(f'caching {name!r} key with await', extra=logdata)
                items = await scraper(self)
            elif inspect.isgeneratorfunction(scraper):
                self._log.debug(f'caching {name!r} key with list', extra=logdata)
                items = list(scraper(self)) 
            elif inspect.isfunction(scraper):
                self._log.debug(f'caching {name!r} key with call', extra=logdata)
                items = scraper(self)
            else:
                self._log.debug(f'caching {name!r} key as value', extra=logdata)
                items = scraper
            self._data[name] = items

        return self._data[name]

    def reset(self):
        for k in self:
            if k not in self.initial_keys and k in self._data:
                _log.debug(f'removing non initial {k!r}')
                del self._data[k]


context = ContextMapping()