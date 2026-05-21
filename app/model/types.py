from typing import Literal

FingerprintType = Literal[
    'chrome', 'firefox', 'safari', 'ios', 'android', 'edge',
    'qq', 'random', 'randomized']

RuleProtocolType = Literal['http', 'tls', 'quic', 'bittorrent']

RoutingDomainStrategyType = Literal['AsIs', 'IPIfNonMatch', 'IPOnDemand']
XrayLogLevel = Literal['none', 'off', 'error', 'info', 'warning', 'debug']
XrayApiServices = Literal['HandlerService', 'LoggerService', 'StatsService', 'RoutingService']
