"""scripts/notify.py TLS enforcement, timeout and bool return."""
import pytest

import scripts.notify as notify_mod


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, context=None, starttls_offered=True):
        self.host, self.port, self.timeout, self.context = host, port, timeout, context
        self.starttls_offered = starttls_offered
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def has_extn(self, name):
        return name == "starttls" and self.starttls_offered

    def starttls(self, context=None):
        self.calls.append(("starttls", context))

    def login(self, user, password):
        self.calls.append("login")

    def send_message(self, msg):
        self.calls.append("send")


@pytest.fixture(autouse=True)
def smtp_env(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setenv("ALERT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("ALERT_SMTP_PORT", "587")
    monkeypatch.setenv("ALERT_SMTP_USER", "alerts@example.com")
    monkeypatch.setenv("ALERT_SMTP_PASSWORD", "secret")
    monkeypatch.delenv("ALERT_SMTP_FROM", raising=False)
    monkeypatch.setattr(notify_mod.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(
        notify_mod.smtplib, "SMTP_SSL",
        lambda *a, **kw: FakeSMTP(*a, **kw),
    )


def _send():
    return notify_mod.notify("subj", "body", recipients=["ops@example.com"])


def test_print_only_without_recipients_returns_true(capsys):
    assert notify_mod.notify("subj", "body", recipients="") is True
    assert FakeSMTP.instances == []
    assert "[NOTIFY] subj" in capsys.readouterr().out


def test_starttls_uses_verifying_context_and_timeout():
    assert _send() is True

    smtp = FakeSMTP.instances[0]
    assert smtp.timeout == notify_mod.SMTP_TIMEOUT_SECONDS
    _, context = smtp.calls[1]
    assert context is not None and context.check_hostname
    assert smtp.calls.index("login") > 1  # login only after STARTTLS
    assert "send" in smtp.calls


def test_refuses_login_without_starttls(monkeypatch):
    monkeypatch.setattr(
        notify_mod.smtplib, "SMTP",
        lambda *a, **kw: FakeSMTP(*a, starttls_offered=False, **kw),
    )

    assert _send() is False
    assert "login" not in FakeSMTP.instances[0].calls


def test_unauthenticated_relay_without_starttls_sends_plain(monkeypatch):
    monkeypatch.delenv("ALERT_SMTP_USER")
    monkeypatch.setenv("ALERT_SMTP_FROM", "alerts@example.com")
    monkeypatch.setattr(
        notify_mod.smtplib, "SMTP",
        lambda *a, **kw: FakeSMTP(*a, starttls_offered=False, **kw),
    )

    assert _send() is True
    assert "login" not in FakeSMTP.instances[0].calls
    assert "send" in FakeSMTP.instances[0].calls


def test_port_465_uses_implicit_tls(monkeypatch):
    monkeypatch.setenv("ALERT_SMTP_PORT", "465")

    assert _send() is True

    smtp = FakeSMTP.instances[0]
    assert smtp.context is not None and smtp.timeout == notify_mod.SMTP_TIMEOUT_SECONDS
    assert not any(isinstance(c, tuple) and c[0] == "starttls" for c in smtp.calls)
    assert "login" in smtp.calls


def test_smtp_error_returns_false(monkeypatch):
    def boom(*a, **kw):
        raise OSError("connection refused")
    monkeypatch.setattr(notify_mod.smtplib, "SMTP", boom)

    assert _send() is False


def test_bad_port_config_returns_false_instead_of_raising(monkeypatch):
    monkeypatch.setenv("ALERT_SMTP_PORT", "abc")

    assert _send() is False
