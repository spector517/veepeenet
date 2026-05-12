from app.view import format_traffic_bytes


class TestFormatTrafficBytes:

    def test_bytes_below_threshold(self):
        assert format_traffic_bytes(0) == '0 B'
        assert format_traffic_bytes(999) == '999 B'

    def test_megabytes(self):
        assert format_traffic_bytes(1_000) == '0.00 MB'
        assert format_traffic_bytes(12_500_000) == '12.50 MB'
        assert format_traffic_bytes(999_999_999) == '1000.00 MB'

    def test_gigabytes(self):
        assert format_traffic_bytes(1_000_000_000) == '1.00 GB'
        assert format_traffic_bytes(3_200_000_000) == '3.20 GB'

    def test_terabytes(self):
        assert format_traffic_bytes(1_000_000_000_000) == '1.00 TB'
        assert format_traffic_bytes(5_500_000_000_000) == '5.50 TB'
