from app.model.shared import Log, Dns, DnsOutbound, DnsServer
from app.model.vless_inbound import VlessInbound, Client, StreamSettings, RealitySettings


class TestLog:

    def test_default_log(self):
        expected_map = {
            'access': 'none',
            'error': '/var/log/xray/error.log',
            'loglevel': 'warning',
            'dnsLog': False,
        }

        log = Log()
        actual_map = log.model_dump(by_alias=True)

        assert actual_map == expected_map

    def test_change_loglevel(self):
        expected_map = {
            'access': 'none',
            'error': '/var/log/xray/error.log',
            'loglevel': 'debug',
            'dnsLog': False,
        }

        log = Log()
        log.loglevel = 'debug'
        actual_map = log.model_dump(by_alias=True)

        assert actual_map == expected_map

    def test_off_loglevel_normalized_to_none(self):
        log = Log(loglevel='off')
        assert log.loglevel == 'none'

    def test_none_loglevel_stays_none(self):
        log = Log(loglevel='none')
        assert log.loglevel == 'none'

    def test_off_loglevel_from_json(self):
        log = Log.model_validate({'loglevel': 'off'})
        assert log.loglevel == 'none'


class TestDns:

    def test_dns(self):
        expected_map = {
            'servers': ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4', '77.88.8.8'],
        }

        dns = Dns()
        dns.servers.append('77.88.8.8') # pylint: disable=no-member
        actual_map = dns.model_dump(by_alias=True)

        assert actual_map == expected_map

    def test_dns_with_server_objects(self):
        dns = Dns(servers=[
            '1.1.1.1',
            DnsServer(address='https://dns.google/dns-query', domains=['example.com']),
        ])
        dumped = dns.model_dump(by_alias=True, exclude_none=True)

        assert dumped == {
            'servers': [
                '1.1.1.1',
                {'address': 'https://dns.google/dns-query', 'domains': ['example.com']},
            ]
        }

    def test_dns_mixed_from_json(self):
        data = {
            'servers': [
                '8.8.8.8',
                {'address': 'https://1.1.1.1/dns-query', 'domains': ['geosite:netflix']},
            ]
        }
        dns = Dns.model_validate(data)
        assert isinstance(dns.servers[0], str)
        assert isinstance(dns.servers[1], DnsServer)
        assert dns.servers[1].address == 'https://1.1.1.1/dns-query'

    def test_dns_server_extra_fields_preserved(self):
        data = {'address': '1.1.1.1', 'clientIp': '5.6.7.8'}
        server = DnsServer.model_validate(data)
        dumped = server.model_dump(by_alias=True, exclude_none=True)
        assert dumped['clientIp'] == '5.6.7.8'


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


class TestDnsOutbound:

    def test_dns_outbound(self):
        expected_map = {
            'tag': 'dns',
            'protocol': 'dns',
            'settings': {
                'nonIPQuery': 'skip'
            },
        }

        dns_outbound = DnsOutbound()
        actual_map = dns_outbound.model_dump(by_alias=True, exclude_none=True)

        assert actual_map == expected_map
