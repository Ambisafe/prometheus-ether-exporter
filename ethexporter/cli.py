import time
from prometheus_aioexporter.script import PrometheusExporterScript
from prometheus_aioexporter.metric import MetricConfig
from functools import lru_cache
import asyncio
import prometheus_client.core
import logging

from . import config, context


_log = logging.getLogger(__name__)


class Web3Exporter(PrometheusExporterScript):
    """WEB3 RPC exporter."""


    def configure_argument_parser(self, parser):
        # Additional arguments to the script
        parser.add_argument('--rpc', nargs='*', default=None, help='Web3 RPC url(s)')
        parser.add_argument('--nodes', nargs='*', default=[], help='Name(s) for RPC url(s)')
        parser.add_argument('--gather', nargs='*', default=None, help=f'Limit gathered metrics to {list(config.metrics.keys())!r}')


    def configure(self, args):
        if args.rpc is not None:
            if len(args.nodes) < len(args.rpc):
                for i in range(len(args.rpc) - len(args.nodes)):
                    args.nodes.append(f'node{i}')
            config.initial['urls'] = dict(zip(args.nodes[:len(args.rpc)], args.rpc))
            context._source['urls'] = config.initial['urls']

        declarations = []
        for name, declaration in self.metrics:
            declarations.append(MetricConfig(name,
                                        declaration['description'],
                                        declaration['type'],
                                        declaration['options']))
        self.create_metrics(declarations)
        self._last_request_time = 0

        if args.gather:
            config.gather = args.gather
        gather = getattr(config, 'gather', None)
        if gather is not None:
            ungather = [metric_name for metric_name in self.registry._metrics if metric_name not in gather]
            for metric_name in ungather:
                del self.registry._metrics[metric_name]
        _log.info('gathering', extra={'metrics': list(self.registry._metrics)})

    async def on_application_startup(self, application):
        await context.initial()
        application['exporter'].set_metric_update_handler(self._update_handler)

    def _iter_metrics(self):
        _metrics = getattr(config, 'metrics', {})
        for name in sorted(_metrics):
            yield name, _metrics[name]


    @property
    @lru_cache(maxsize=1)
    def metrics(self):
        return list(self._iter_metrics())


    async def _update_handler(self, application):
        # Stop other asyncio tasks at application shutdown
        _request_delta = time.time() - self._last_request_time
        if  _request_delta > config.scrape_throttle:
            _log.debug('args', extra=application)
            await self.scrape_metrics(application)
            context.reset() #contextvar support in asyncio added only in py37
            self._last_request_time = time.time()
        else:
            _log.debug(f'throttling after {_request_delta!r}')



    async def scrape_metrics(self, application):
        for name, declaration in self.metrics:
            if name not in application:
                continue
            _log.debug(f'{name!r}')
            metric = application[name]
            for labeled in await context[name]:
                if isinstance(metric, prometheus_client.core._LabelWrapper):
                    label_formats = declaration.get('options', {}).get('labels', {})
                    labels = dict((k, v.format(**labeled.labels)) for (k, v) in label_formats.items())
                    _metric = metric.labels(**dict(labels))
                else:
                    _metric = metric
                    labels = {}
                declaration['setter'](_metric)(labeled.value)
                _log.debug('exposed', extra={'key':name, 'value': labeled.value, 'labels':labels})


exporter = Web3Exporter()