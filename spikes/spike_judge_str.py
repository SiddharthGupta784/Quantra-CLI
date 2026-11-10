"""Spike: does a judge that returns a raw JSON *string* (ignoring schema) still work?"""
from spike_judge import FakeJudge, canned, tc  # noqa: F401  (runs the first spike too)
from deepeval.metrics import AnswerRelevancyMetric


class StrJudge(FakeJudge):
    def generate(self, prompt, schema=None, **kw):
        return canned(schema) if schema else "{}"

    async def a_generate(self, prompt, schema=None, **kw):
        return canned(schema) if schema else "{}"


for mode in (False, True):
    m = AnswerRelevancyMetric(model=StrJudge(), async_mode=mode)
    m.measure(tc)
    print(f"STR-RETURN async_mode={mode}: score={m.score}")
