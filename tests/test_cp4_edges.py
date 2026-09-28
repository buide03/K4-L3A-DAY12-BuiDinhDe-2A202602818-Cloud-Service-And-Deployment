"""CP4 shutdown precedence and repeated-registration regressions."""

import signal

from app.lifecycle import Lifecycle, lifecycle


def test_repeated_install_forwards_once(monkeypatch):
    calls = []
    previous = lambda signum, frame: calls.append(signum)
    handlers = {signal.SIGTERM: previous, signal.SIGINT: previous}
    monkeypatch.setattr(signal, "getsignal", handlers.get)
    monkeypatch.setattr(signal, "signal", lambda sig, handler: handlers.__setitem__(sig, handler))
    life = Lifecycle()
    life.install()
    life.install()
    life.request_shutdown(signal.SIGTERM, None)
    assert life.shutting_down
    assert calls == [signal.SIGTERM]


def test_shutdown_readiness_does_not_ping_redis(client_factory):
    class MustNotPing:
        def ping(self):
            raise AssertionError("Shutdown readiness must not ping Redis")

    client = client_factory(store=MustNotPing())
    lifecycle.shutting_down = True
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "shutting_down"}
