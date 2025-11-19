import types

import pytest

pytest.importorskip('flask_caching')
pytest.importorskip('flask_sqlalchemy')

from config import TestingConfig
from meu_app import create_app
from meu_app.queue import enqueue_pdf_job, enqueue_receipt_cleanup_job
import meu_app.queue as queue_module


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        yield app


def test_enqueue_pdf_job_returns_none_without_queue(app, monkeypatch):
    monkeypatch.setattr(queue_module, 'pdf_queue', None)
    assert enqueue_pdf_job({'pedido_id': 1}) is None


def test_enqueue_pdf_job_enqueues_when_queue_available(app, monkeypatch):
    calls = []

    class DummyJob:
        def __init__(self, job_id='fake-job'):
            self.id = job_id

    class DummyQueue:
        def enqueue(self, func, payload, **kwargs):
            calls.append((func, payload, kwargs))
            return DummyJob('job-123')

    monkeypatch.setattr(queue_module, 'pdf_queue', DummyQueue())
    job_id = enqueue_pdf_job({'pedido_id': 42})
    assert job_id == 'job-123'
    assert calls, 'enqueue should have been called'


def test_receipt_cleanup_job_handles_missing_queue(app, monkeypatch):
    monkeypatch.setattr(queue_module, 'pdf_queue', None)
    assert enqueue_receipt_cleanup_job() is None
