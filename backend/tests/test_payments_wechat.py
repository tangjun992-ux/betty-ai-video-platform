"""WeChat Pay notify verification."""
from unittest.mock import MagicMock, patch

from app.services import payments


def test_verify_wechat_notify_returns_none_when_not_live():
    with patch.object(payments, "wechat_live", return_value=False):
        assert payments.verify_wechat_notify({}, b"{}") is None


def test_verify_wechat_notify_uses_callback_when_live():
    fake_payload = {"event_type": "TRANSACTION.SUCCESS", "resource": {"out_trade_no": "o1", "trade_state": "SUCCESS"}}
    mock_wx = MagicMock()
    mock_wx.callback.return_value = fake_payload
    with patch.object(payments, "wechat_live", return_value=True):
        with patch.object(payments, "_wxpay_client", return_value=mock_wx):
            out = payments.verify_wechat_notify({"Wechatpay-Signature": "sig"}, '{"id":"x"}')
    assert out == fake_payload
    mock_wx.callback.assert_called_once()


def test_verify_wechat_notify_returns_none_on_callback_failure():
    mock_wx = MagicMock()
    mock_wx.callback.return_value = None
    with patch.object(payments, "wechat_live", return_value=True):
        with patch.object(payments, "_wxpay_client", return_value=mock_wx):
            assert payments.verify_wechat_notify({}, "{}") is None
