import inspect

import deepeval.test_case as tcmod
import deepeval.metrics as mm
import deepeval.synthesizer as sm
from deepeval.synthesizer import Synthesizer

print("== test_case exports:", [n for n in dir(tcmod) if not n.startswith("_")])
print("== metrics with 'onversation'/'Retention'/'Completeness':",
      [n for n in dir(mm) if any(k in n for k in ("onversation", "Retention", "Completeness", "Role", "Turn"))])
print("== synthesizer exports:", [n for n in dir(sm) if not n.startswith("_")])
print("== Synthesizer.__init__", inspect.signature(Synthesizer.__init__))
print("== Synthesizer public methods:", [n for n in dir(Synthesizer) if not n.startswith("_")])
for n in ("generate_goldens_from_scratch", "generate_goldens_from_contexts"):
    print(f"== {n}", inspect.signature(getattr(Synthesizer, n)))
for n in ("generate_conversational_goldens_from_scratch", "generate_conversational_goldens_from_contexts"):
    if hasattr(Synthesizer, n):
        print(f"== {n}", inspect.signature(getattr(Synthesizer, n)))
for cls in ("ConversationalTestCase", "Turn", "ConversationalGolden", "Golden"):
    obj = getattr(tcmod, cls, None) or getattr(__import__("deepeval.dataset", fromlist=[cls]), cls, None)
    print(f"== {cls}", inspect.signature(obj.__init__) if obj else "MISSING")
try:
    from deepeval.conversation_simulator import ConversationSimulator
    print("== ConversationSimulator", inspect.signature(ConversationSimulator.__init__))
    print("   methods:", [n for n in dir(ConversationSimulator) if not n.startswith("_")])
except Exception as e:
    print("== ConversationSimulator import failed:", e)
