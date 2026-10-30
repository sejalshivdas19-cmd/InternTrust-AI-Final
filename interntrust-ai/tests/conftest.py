import pytest

from app import create_app
from app.extensions import db as _db
from app.models import RiskSignal
from app.services.risk_signals_data import DEFAULT_RISK_SIGNALS


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        for signal in DEFAULT_RISK_SIGNALS:
            _db.session.add(RiskSignal(**signal))
        _db.session.commit()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db
