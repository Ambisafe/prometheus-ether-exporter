import time
from prometheus_aioexporter.script import PrometheusExporterScript
from prometheus_aioexporter.metric import MetricConfig
from functools import lru_cache
import asyncio
import aiohttp
import prometheus_client.core
import logging
import sys
from toolrack.log import setup_logger

from . import config, context


_log = logging.getLogger(__name__)


class Web3Exporter(PrometheusExporterScript):
    """WEB3 RPC exporter."""


    def configure_argument_parser(self, parser):
        # Additional arguments to the script
        parser.add_argument('--rpc', nargs='*', default=None, help='Web3 RPC url(s)')
        parser.add_argument('--nodes', nargs='*', default=[], help='Name(s) for RPC url(s)')
        parser.add_argument('--gather', nargs='*', default=None, help=f'Limit gathered metrics to {list(config.metrics.keys())!r}')
        parser.add_argument('--etherscan-lastblock-url', default=config.metrics['etherscan_lastblock_number']['options']['etherscan_url'], help=f"Url for etherscan lastblock request")

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
        config.metrics['etherscan_lastblock_number']['options']['etherscan_url'] = args.etherscan_lastblock_url
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
        try:
            _request_delta = time.time() - self._last_request_time
            if  _request_delta > config.scrape['throttle']:
                _log.debug('args', extra=application)
                await self.scrape_metrics(application)
                await context.reset() #contextvar support in asyncio added only in py37
                self._last_request_time = time.time()
            else:
                _log.debug(f'throttling after {_request_delta!r}')
        except asyncio.CancelledError as e:
            log.exception(e)

    async def scrape_metrics(self, application):
        for name, declaration in self.metrics:
            if name not in application:
                continue
            _log.debug(f'{name!r}')
            metric = application[name]
            async for labeled in context[name]:
                if labeled is None:
                    continue
                if isinstance(metric, prometheus_client.core._LabelWrapper):
                    label_formats = declaration.get('options', {}).get('labels', {})
                    labels = dict((k, v.format(**labeled.labels)) for (k, v) in label_formats.items())
                    _metric = metric.labels(**dict(labels))
                else:
                    _metric = metric
                    labels = {}
                declaration['setter'](_metric)(labeled.value)
                _log.debug('exposed', extra={'key':name, 'value': labeled.value, 'labels':labels})

    def _setup_logging(self, log_level):
        """Setup logging for the application and aiohttp."""
        level = getattr(logging, log_level)
        names = (
            'aiohttp.access', 'aiohttp.internal', 'aiohttp.server',
            'aiohttp.web', 'aiohttp.client', 'asyncio_client', self.name)
        for name in names:
            setup_logger(name=name, stream=sys.stderr, level=level)

exporter = Web3Exporter()