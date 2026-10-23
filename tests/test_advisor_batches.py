"""Request pacing and cancellation without wall-clock waits or real transport."""
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
import pytest
from langgraphagenticai.providers.advisor_batches import RequestBatch, CollectionStopped
from langgraphagenticai.providers.fmp_http import ProviderRequestError


def test_every_hundred_requests_pause_thirty_seconds_and_use_read_timeout():
    waits=[];request=Mock(return_value="ok");budget=RequestBatch(wait=waits.append)
    for _ in range(201):
        assert budget.request(request,"fixture",timeout=(1,1))=="ok"
    assert waits==[30,30] and request.call_count==201
    assert all(c.kwargs["timeout"]==(3,30) for c in request.call_args_list)


def test_workers_share_the_same_hundred_request_gate():
    waits=[];budget=RequestBatch(wait=waits.append)
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(lambda i:budget.request(lambda **kwargs:i),range(203)))==list(range(203))
    assert waits==[30,30]


def test_rate_limit_stops_following_calls_without_wait_or_retry():
    waits=[];budget=RequestBatch(wait=waits.append)
    request=Mock(side_effect=ProviderRequestError("FMP","fixture-secret",status_code=429))
    with pytest.raises(ProviderRequestError):budget.request(request,"fixture")
    with pytest.raises(CollectionStopped):budget.request(request,"fixture")
    assert request.call_count==1 and not waits and "fixture-secret" not in budget.warning


def test_macro_reservation_fits_within_hundred_or_waits():
    waits=[];budget=RequestBatch(wait=waits.append)
    for _ in range(80):budget.request(lambda **kwargs:None)
    budget.reserve(24)
    assert waits==[30]
    for _ in range(76):budget.request(lambda **kwargs:None)
    assert waits==[30]
    budget.request(lambda **kwargs:None)
    assert waits==[30,30]


def test_stop_during_cooldown_prevents_the_next_request():
    budget=RequestBatch(wait=lambda seconds:budget.stopped.set())
    request=Mock()
    for _ in range(100):budget.request(request)
    with pytest.raises(CollectionStopped):budget.request(request)
    assert request.call_count==100
