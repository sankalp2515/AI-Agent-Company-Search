import threading
import time

from orglens.core import envelope,fetch_robots
from test_integrity_fixes import snapshot


class Robots:
    def __init__(self,statuses,budget=False,retry_after=None):
        self.statuses=statuses;self.calls=0;self.deadline=time.monotonic()+60
        self.lock=threading.Lock();self.host_delays={};self.budget=budget
        self.retry_after=retry_after
    def get(self,url,source_class):
        status=self.statuses[min(self.calls,len(self.statuses)-1)];self.calls+=1
        return {**snapshot('User-agent: *\nDisallow: /private',url),'status':status,'budget_exhausted':self.budget,'retry_after':self.retry_after}


def test_transient_robots_failure_is_retried_before_abstaining():
    transport=Robots([503,200])
    robot,state=fetch_robots(envelope('123456789','test'),'https://example.no/','example.no',transport)
    assert transport.calls==2 and state is None
    assert robot.can_fetch('OrgLens','https://example.no/public')
    assert not robot.can_fetch('OrgLens','https://example.no/private')


def test_robots_budget_failure_is_not_retried():
    transport=Robots([0],budget=True)
    robot,state=fetch_robots(envelope('123456789','test'),'https://example.no/','example.no',transport)
    assert robot is None and transport.calls==1


def test_persistent_robots_rate_limit_is_not_permission_to_crawl():
    transport=Robots([429])
    robot,state=fetch_robots(envelope('123456789','test'),'https://example.no/','example.no',transport)
    assert robot is None and state=='blocked' and transport.calls==2


def test_long_source_backoff_does_not_retry_or_hold_the_batch(monkeypatch):
    transport=Robots([429],retry_after='120')
    monkeypatch.setattr(time,'sleep',lambda delay:(_ for _ in ()).throw(AssertionError('must abstain instead of sleeping')))
    robot,state=fetch_robots(envelope('123456789','test'),'https://example.no/','example.no',transport)
    assert robot is None and state=='blocked' and transport.calls==1
