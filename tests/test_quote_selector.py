import json
import time
import pytest
from orglens.core import envelope


class Transport:
    deadline=time.monotonic()+60
    def __init__(self):self.requests=0
    def reserve(self,url):self.requests+=1


def test_model_can_select_only_literal_existing_quote():
    from orglens.quotes import QuoteSelector
    model={'name':'groq','model':'test','url':'https://example.test','key':'test'}
    reply=lambda *args:{'choices':[{'message':{'content':json.dumps({'description_index':1})}}],'usage':{'prompt_tokens':20,'completion_tokens':5}}
    selector=QuoteSelector(model,max_calls=2,caller=reply)
    options=['We use cookies for analytics on the web site.','Example AS manufactures industrial pumps for Norwegian fisheries.']
    assert selector.select_description('Example AS',options,Transport())==options[1]
    assert selector.report()['successful_selections']==1


def test_json_mode_request_explicitly_requests_json_and_disables_builtin_tools():
    from orglens.quotes import QuoteSelector
    def reply(url,key,body,timeout):
        assert 'json' in ' '.join(m['content'] for m in body['messages']).lower()
        assert body['tool_choice']=='none'
        return {'choices':[{'message':{'content':'{"description_index":0}'}}]}
    selector=QuoteSelector({'name':'groq','model':'test','url':'https://example.test','key':'test'},caller=reply)
    assert selector.select_description('Example AS',['Example AS manufactures marine equipment.'],Transport())


def test_provider_errors_are_counted_without_logging_secret_or_body():
    from orglens.quotes import QuoteSelector
    from orglens.agent import ProviderError
    def fail(*args):raise ProviderError(400,['json'])
    selector=QuoteSelector({'name':'groq','model':'test','url':'https://example.test','key':'secret-test'},caller=fail)
    assert selector.select_description('Example AS',['Example AS manufactures marine equipment.'],Transport()) is None
    assert selector.report()['failure_types']=={'provider_http_400':1}
    assert 'secret-test' not in json.dumps(selector.report())


@pytest.mark.parametrize('answer',[{'description_index':99},{'description_index':True},{'description_index':0,'invented_fact':'Revenue is 5 million'}])
def test_model_cannot_invent_a_quote_or_fields(answer):
    from orglens.quotes import QuoteSelector
    reply=lambda *args:{'choices':[{'message':{'content':json.dumps(answer)}}]}
    selector=QuoteSelector({'name':'groq','model':'test','url':'https://example.test','key':'test'},caller=reply)
    assert selector.select_description('Example AS',['Example AS supplies pumps to maritime customers.'],Transport()) is None


def test_model_quote_calls_have_shared_cap():
    from orglens.quotes import QuoteSelector
    reply=lambda *args:{'choices':[{'message':{'content':'{"description_index":0}'}}]}
    selector=QuoteSelector({'name':'groq','model':'test','url':'https://example.test','key':'test'},max_calls=1,caller=reply)
    t=Transport()
    for _ in range(3):selector.select_description('Example AS',['Example AS supplies pumps to maritime customers.'],t)
    assert t.requests==1
