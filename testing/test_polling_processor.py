import pytest
import threading
import time

from ldclient.config import Config
from ldclient.feature_store import InMemoryFeatureStore
from ldclient.interfaces import FeatureRequester
from ldclient.polling import PollingUpdateProcessor
from ldclient.util import UnsuccessfulResponseException
from ldclient.versioned_data_kind import FEATURES, SEGMENTS
from testing.stub_util import MockFeatureRequester, MockResponse

config = Config()
pp = None
mock_requester = None
store = None
ready = None


def setup_function():
    global mock_requester, store, ready
    mock_requester = MockFeatureRequester()
    store = InMemoryFeatureStore()
    ready = threading.Event()

def teardown_function():
    if pp is not None:
        pp.stop()

def setup_processor(config):
    global pp
    pp = PollingUpdateProcessor(config, mock_requester, store, ready)
    pp.start()

def test_successful_request_puts_feature_data_in_store():
    flag = {
        "key": "flagkey"
    }
    segment = {
        "key": "segkey"
    }
    mock_requester.all_data = {
        FEATURES: {
            "flagkey": flag
        },
        SEGMENTS: {
            "segkey": segment
        }
    }
    setup_processor(config)
    ready.wait()
    assert store.get(FEATURES, "flagkey", lambda x: x) == flag
    assert store.get(SEGMENTS, "segkey", lambda x: x) == segment
    assert store.initialized
    assert pp.initialized()

def test_general_connection_error_does_not_cause_immediate_failure():
    mock_requester.exception = Exception("bad")
    start_time = time.time()
    setup_processor(config)
    ready.wait(0.3)
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 0.2
    assert not pp.initialized()

def test_http_401_error_causes_immediate_failure():
    mock_requester.exception = UnsuccessfulResponseException(401)
    start_time = time.time()
    setup_processor(config)
    ready.wait(5.0)
    elapsed_time = time.time() - start_time
    assert elapsed_time < 5.0
    assert not pp.initialized()