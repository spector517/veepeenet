from app.view import ClientView, format_traffic_bytes


class TestFormatTrafficBytes:

    def test_bytes_below_threshold(self):
        assert format_traffic_bytes(0) == '0 B'
        assert format_traffic_bytes(999) == '999 B'

    def test_kilobytes(self):
        assert format_traffic_bytes(1_000) == '1.00 KB'
        assert format_traffic_bytes(12_500) == '12.50 KB'
        assert format_traffic_bytes(999_999) == '1000.00 KB'

    def test_megabytes(self):
        assert format_traffic_bytes(1_000_000) == '1.00 MB'
        assert format_traffic_bytes(12_500_000) == '12.50 MB'
        assert format_traffic_bytes(999_999_999) == '1000.00 MB'

    def test_gigabytes(self):
        assert format_traffic_bytes(1_000_000_000) == '1.00 GB'
        assert format_traffic_bytes(3_200_000_000) == '3.20 GB'

    def test_terabytes(self):
        assert format_traffic_bytes(1_000_000_000_000) == '1.00 TB'
        assert format_traffic_bytes(5_500_000_000_000) == '5.50 TB'


class TestClientViewDisabled:

    def test_rich_repr_short_marks_enabled_client(self):
        view = ClientView(name='alice', url='vless://test', disabled=False)

        assert view.rich_repr_short().plain == '● alice'

    def test_rich_repr_short_marks_disabled_client(self):
        view = ClientView(name='alice', url='vless://test', disabled=True)

        assert view.rich_repr_short().plain == '● alice'

    def test_rich_repr_marks_disabled_client(self):
        view = ClientView(name='alice', url='vless://test', disabled=True)
        group = view.rich_repr()
        rendered = list(group.renderables)

        assert rendered[0].plain.startswith('● alice')
