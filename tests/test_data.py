from app.model.api import Stats
from app.controller.data import StatsData
from app.model.veepeenet import VeePeeNetStats


def _stat(name: str, value: int | None = 0) -> Stats:
    return Stats(name=name, value=value)


class TestStatsDataFromApi:

    def test_parses_inbound_uplink(self):
        stat = _stat('inbound>>>vless-inbound>>>traffic>>>uplink', 1000)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.subject == StatsData.SubjectType.INBOUND
        assert result.name == 'vless-inbound'
        assert result.direction == StatsData.DirectionType.UPLINK
        assert result.traffic == 1000

    def test_parses_inbound_downlink(self):
        stat = _stat('inbound>>>vless-inbound>>>traffic>>>downlink', 500)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.subject == StatsData.SubjectType.INBOUND
        assert result.direction == StatsData.DirectionType.DOWNLINK
        assert result.traffic == 500

    def test_parses_user_downlink(self):
        stat = _stat('user>>>alice.abc@0.0.0.0>>>traffic>>>downlink', 2000)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.subject == StatsData.SubjectType.CLIENT
        assert result.name == 'alice'
        assert result.direction == StatsData.DirectionType.DOWNLINK
        assert result.traffic == 2000

    def test_parses_outbound_direct(self):
        stat = _stat('outbound>>>direct>>>traffic>>>uplink', 300)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.subject == StatsData.SubjectType.OUTBOUND
        assert result.name == 'direct'
        assert result.traffic == 300

    def test_parses_outbound_blackhole(self):
        stat = _stat('outbound>>>blackhole>>>traffic>>>uplink', 999)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.name == 'blackhole'

    def test_parses_outbound_dns(self):
        stat = _stat('outbound>>>dns>>>traffic>>>downlink', 111)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.name == 'dns'

    def test_returns_none_for_malformed_name(self):
        assert StatsData.from_api(_stat('not>>>valid')) is None
        assert StatsData.from_api(_stat('only_one_part')) is None
        assert StatsData.from_api(_stat('a>>>b>>>c>>>d>>>e')) is None

    def test_returns_none_for_non_traffic_type(self):
        stat = _stat('inbound>>>vless-inbound>>>stats>>>uplink', 100)
        result = StatsData.from_api(stat)
        assert result is None

    def test_returns_none_for_unknown_subject(self):
        stat = _stat('badtype>>>something>>>traffic>>>uplink', 100)
        result = StatsData.from_api(stat)
        assert result is None

    def test_returns_none_for_unknown_direction(self):
        stat = _stat('inbound>>>vless-inbound>>>traffic>>>sideways', 100)
        result = StatsData.from_api(stat)
        assert result is None

    def test_handles_none_value(self):
        stat = _stat('inbound>>>vless-inbound>>>traffic>>>uplink', None)
        result = StatsData.from_api(stat)
        assert result is not None
        assert result.traffic == 0


class TestStatsDataToModel:

    def test_inbound_uplink_to_model(self):
        data = StatsData(
            subject=StatsData.SubjectType.INBOUND,
            name='vless-inbound',
            direction=StatsData.DirectionType.UPLINK,
            traffic=1000,
        )
        model = data.to_model()
        assert isinstance(model, VeePeeNetStats)
        assert model.inbound['vless-inbound'].uplink == 1000
        assert model.inbound['vless-inbound'].downlink == 0
        assert model.client == {}
        assert model.outbound == {}

    def test_inbound_downlink_to_model(self):
        data = StatsData(
            subject=StatsData.SubjectType.INBOUND,
            name='vless-inbound',
            direction=StatsData.DirectionType.DOWNLINK,
            traffic=500,
        )
        model = data.to_model()
        assert model.inbound['vless-inbound'].downlink == 500
        assert model.inbound['vless-inbound'].uplink == 0

    def test_user_downlink_to_model(self):
        data = StatsData(
            subject=StatsData.SubjectType.CLIENT,
            name='alice.abc@0.0.0.0',
            direction=StatsData.DirectionType.DOWNLINK,
            traffic=2000,
        )
        model = data.to_model()
        assert model.client['alice.abc@0.0.0.0'].downlink == 2000
        assert model.inbound == {}
        assert model.outbound == {}

    def test_outbound_uplink_to_model(self):
        data = StatsData(
            subject=StatsData.SubjectType.OUTBOUND,
            name='direct',
            direction=StatsData.DirectionType.UPLINK,
            traffic=300,
        )
        model = data.to_model()
        assert model.outbound['direct'].uplink == 300
        assert model.client == {}
        assert model.inbound == {}

    def test_outbound_blackhole_to_model(self):
        data = StatsData(
            subject=StatsData.SubjectType.OUTBOUND,
            name='blackhole',
            direction=StatsData.DirectionType.UPLINK,
            traffic=999,
        )
        model = data.to_model()
        assert model.outbound['blackhole'].uplink == 999
