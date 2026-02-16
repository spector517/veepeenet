import pytest
from pydantic import ValidationError

from app.model.routing import Routing, Rule
from app.model.shared import Log, Dns, DnsOutbound
from app.model.vless_inbound import VlessInbound, Client, StreamSettings, RealitySettings


class TestLog:

    def test_default_log(self):
        expected_map = {
            'access': '/var/log/xray/access.log',
            'error': '/var/log/xray/error.log',
            'loglevel': 'off',
            'dnsLog': False,
        }

        log = Log()
        actual_map = log.model_dump(by_alias=True)

        assert actual_map == expected_map

    def test_change_loglevel(self):
        expected_map = {
            'access': '/var/log/xray/access.log',
            'error': '/var/log/xray/error.log',
            'loglevel': 'debug',
            'dnsLog': False,
        }

        log = Log()
        log.loglevel = 'debug'
        actual_map = log.model_dump(by_alias=True)

        assert actual_map == expected_map


class TestDns:

    def test_dns(self):
        expected_map = {
            'servers': ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4', '77.88.8.8'],
        }

        dns = Dns()
        dns.servers.append('77.88.8.8') # pylint: disable=no-member
        actual_map = dns.model_dump(by_alias=True)

        assert actual_map == expected_map


class TestClient:

    def test_client(self):
        expected_map = {
            'email': 'some_email',
            'id': 'some_id',
            'flow': 'xtls-rprx-vision',
        }

        client = Client(id='some_id', email='some_email')
        actual_map = client.model_dump(by_alias=True)

        assert actual_map == expected_map


class TestVlessInbound:

    def test_vless_inbound(self):
        expected_map = {
            'listen': '0.0.0.0',
            'port': 443,
            'protocol': 'vless',
            'tag': 'vless-inbound',
            'settings': {
                'clients': [],
                'decryption': 'none'
            },
            'streamSettings': {
                'security': 'reality',
                'realitySettings': {
                    'dest': 'yahoo.com:443',
                    'serverNames': ['yahoo.com'],
                    'privateKey': 'very-secret-key',
                    'shortIds': [],
                }
            },
            'sniffing': {
                'enabled': False,
                'routeOnly': True,
                'destOverride': ['http', 'tls', 'quic'],
            }
        }

        vless_inbound = VlessInbound(
            listen='0.0.0.0',
            port=443,
            stream_settings=StreamSettings(
                reality_settings=RealitySettings(
                    dest='yahoo.com:443',
                    server_names=['yahoo.com'],
                    private_key='very-secret-key',
                    short_ids=[])))
        actual_map = vless_inbound.model_dump(by_alias=True)

        assert actual_map == expected_map


class TestRouting:

    def test_routing_no_rules(self):
        with pytest.raises(ValidationError):
            Rule(tag='empty-rule', outbound_tag='empty-outbound')

    def test_routing_with_rules(self):
        expected_map = {
            'domainStrategy': 'AsIs',
            'rules': [
                {
                    'port': '123',
                    'tag': 'port-rule',
                    'outboundTag': 'empty-outbound',
                },
                {
                    'domain': ['example.com'],
                    'tag': 'domain-rule',
                    'outboundTag': 'empty-outbound',
                }
            ]
        }

        port_rule = Rule(tag='port-rule', outbound_tag='empty-outbound', port='123')
        domain_rule = Rule(tag='domain-rule', outbound_tag='empty-outbound', domain=['example.com'])
        routing = Routing(rules=[port_rule, domain_rule])
        actual_map = routing.model_dump(by_alias=True, exclude_none=True)

        assert actual_map == expected_map


class TestDnsOutbound:

    def test_dns_outbound(self):
        expected_map = {
            'tag': 'dns',
            'protocol': 'dns',
            'settings': {
                'network': 'tcp',
                'nonIPQuery': 'skip'
            },
        }

        dns_outbound = DnsOutbound()
        actual_map = dns_outbound.model_dump(by_alias=True)

        assert actual_map == expected_map
