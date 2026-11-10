"""Spike: Synthesizer + ConversationSimulator + conversation metrics with a generic fake judge."""
import json
import sys
import typing

from deepeval.models import DeepEvalBaseLLM
from pydantic import BaseModel

SEEN: list[str] = []


def fill(tp, depth=0):
    """Build a minimal valid value for a type annotation."""
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        return fill(non_none[0], depth) if non_none else None
    if origin in (list, typing.List):
        return [fill(args[0], depth + 1)] if depth < 3 else []
    if origin in (dict, typing.Dict):
        return {}
    if origin is typing.Literal:
        return args[0]
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return {n: fill(f.annotation, depth + 1) for n, f in tp.model_fields.items()}
    if tp is str:
        return "canned text"
    if tp is bool:
        return True
    if tp is int:
        return 8
    if tp is float:
        return 0.9
    return None


class Fake(DeepEvalBaseLLM):
    def __init__(self):
        super().__init__(model="fake")

    def load_model(self):
        return self

    def _run(self, prompt, schema):
        name = getattr(schema, "__name__", None)
        SEEN.append(f"{name}: {list(schema.model_fields) if schema else None}")
        if schema is None:
            return "canned text"
        return schema.model_validate(fill(schema))

    def generate(self, prompt, schema=None, **kw):
        return self._run(prompt, schema)

    async def a_generate(self, prompt, schema=None, **kw):
        return self._run(prompt, schema)

    def get_model_name(self):
        return "fake"


def section(t):
    print(f"\n##### {t}")


section("Synthesizer.generate_goldens_from_scratch (scenario via StylingConfig)")
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import StylingConfig

SEEN.clear()
try:
    s = Synthesizer(
        model=Fake(),
        async_mode=False,
        styling_config=StylingConfig(
            scenario="Test refund policy edge cases for premium users.",
            task="Customer-support agent answering refund questions",
            input_format="A short customer question",
            expected_output_format="A concise policy-grounded answer",
        ),
    )
    goldens = s.generate_goldens_from_scratch(num_goldens=2)
    print("goldens:", len(goldens), [(g.input, g.expected_output) for g in goldens][:2])
except Exception as e:  # noqa: BLE001
    print("FAILED:", type(e).__name__, e)
print("schemas requested:", SEEN)

section("Synthesizer.generate_goldens_from_contexts (scenario text as context)")
SEEN.clear()
try:
    goldens = Synthesizer(model=Fake(), async_mode=False).generate_goldens_from_contexts(
        contexts=[["Premium users can get refunds within 60 days."]], max_goldens_per_context=1
    )
    print("goldens:", len(goldens), [(g.input, g.expected_output) for g in goldens][:2])
except Exception as e:  # noqa: BLE001
    print("FAILED:", type(e).__name__, e)
print("schemas requested:", SEEN)

section("generate_conversational_goldens_from_scratch")
SEEN.clear()
try:
    from deepeval.synthesizer.config import ConversationalStylingConfig

    cs = Synthesizer(
        model=Fake(),
        async_mode=False,
        conversational_styling_config=ConversationalStylingConfig(
            scenario_context="Refund requests for premium users",
            conversational_task="Resolve a refund request",
            participant_roles="customer and support agent",
        ),
    )
    cg = cs.generate_conversational_goldens_from_scratch(num_goldens=1)
    print("conv goldens:", len(cg), [(g.scenario, g.expected_outcome) for g in cg])
except Exception as e:  # noqa: BLE001
    print("FAILED:", type(e).__name__, e)
print("schemas requested:", SEEN)

section("ConversationSimulator with callback")
from deepeval.dataset import ConversationalGolden
from deepeval.simulator import ConversationSimulator
from deepeval.test_case import Turn

SEEN.clear()


def agent(input: str, turns: list, thread_id: str) -> Turn:
    return Turn(role="assistant", content=f"echo: {input[:40]}")


try:
    sim = ConversationSimulator(model_callback=agent, simulator_model=Fake(), async_mode=False)
    cases = sim.simulate(
        [ConversationalGolden(scenario="Customer wants a refund", expected_outcome="Refund approved",
                              user_description="Premium customer")],
        max_user_simulations=2,
    )
    print("cases:", len(cases), "turns:", [(t.role, t.content) for t in cases[0].turns])
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
print("schemas requested:", SEEN)

section("Conversation metrics")
from deepeval.metrics import (
    ConversationCompletenessMetric,
    KnowledgeRetentionMetric,
    TurnRelevancyMetric,
)
from deepeval.test_case import ConversationalTestCase

ctc = ConversationalTestCase(
    turns=[
        Turn(role="user", content="I want a refund"),
        Turn(role="assistant", content="Sure, what is your order id?"),
        Turn(role="user", content="A123"),
        Turn(role="assistant", content="Refund issued for A123."),
    ],
    expected_outcome="Refund issued",
)
for M in (ConversationCompletenessMetric, KnowledgeRetentionMetric, TurnRelevancyMetric):
    SEEN.clear()
    try:
        m = M(model=Fake(), async_mode=False)
        m.measure(ctc)
        print(M.__name__, "score=", m.score, "schemas:", [x.split(":")[0] for x in SEEN])
    except Exception as e:  # noqa: BLE001
        print(M.__name__, "FAILED:", type(e).__name__, str(e)[:200], "schemas:", SEEN)
sys.stdout.flush()
