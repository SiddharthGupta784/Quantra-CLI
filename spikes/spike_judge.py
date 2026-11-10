"""Spike: custom DeepEvalBaseLLM + AnswerRelevancyMetric + GEval with a canned fake judge."""
import asyncio
import json

from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, SingleTurnParams

CALLS: list[dict] = []


def canned(schema) -> str:
    """Return JSON valid for the requested pydantic schema (spike: dispatch on schema name)."""
    name = getattr(schema, "__name__", str(schema))
    fields = list(getattr(schema, "model_fields", {}))
    if name == "Statements":
        return json.dumps({"statements": ["The refund window is 30 days."]})
    if name == "Verdicts":
        return json.dumps({"verdicts": [{"verdict": "yes", "reason": None}]})
    if set(fields) == {"score", "reason"}:
        return json.dumps({"score": 9, "reason": "canned"})
    if fields == ["steps"]:
        return json.dumps({"steps": ["check relevance", "check correctness"]})
    if fields == ["reason"]:
        return json.dumps({"reason": "canned reason"})
    return json.dumps({f: None for f in fields})


class FakeJudge(DeepEvalBaseLLM):
    def __init__(self):
        super().__init__(model="fake-judge")

    def load_model(self):
        CALLS.append({"event": "load_model"})
        return self

    def generate(self, prompt: str, schema=None, **kw):
        CALLS.append({"event": "generate", "schema": getattr(schema, "__name__", None), "kw": list(kw)})
        out = canned(schema) if schema else "{}"
        return schema.model_validate_json(out) if schema else out

    async def a_generate(self, prompt: str, schema=None, **kw):
        CALLS.append({"event": "a_generate", "schema": getattr(schema, "__name__", None), "kw": list(kw)})
        out = canned(schema) if schema else "{}"
        return schema.model_validate_json(out) if schema else out

    def get_model_name(self):
        return "fake-judge"


tc = LLMTestCase(
    input="What is the refund window?",
    actual_output="Refunds are accepted within 30 days.",
    expected_output="30 days",
)

for async_mode in (False, True):
    CALLS.clear()
    judge = FakeJudge()
    ar = AnswerRelevancyMetric(model=judge, async_mode=async_mode, threshold=0.5)
    ar.measure(tc)
    print(f"AnswerRelevancy async_mode={async_mode}: score={ar.score} success={ar.is_successful()}")
    print("  calls:", [(c["event"], c.get("schema")) for c in CALLS])

    CALLS.clear()
    ge = GEval(
        name="Correctness",
        criteria="Is the actual output factually consistent with the expected output?",
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        model=judge,
        async_mode=async_mode,
    )
    ge.measure(tc)
    print(f"GEval async_mode={async_mode}: score={ge.score} success={ge.is_successful()}")
    print("  calls:", [(c["event"], c.get("schema")) for c in CALLS])

# a_measure path
CALLS.clear()
ar = AnswerRelevancyMetric(model=FakeJudge())
asyncio.run(ar.a_measure(tc))
print("a_measure:", ar.score, [(c["event"], c.get("schema")) for c in CALLS])
