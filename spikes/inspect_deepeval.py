import inspect, deepeval
from deepeval.models import DeepEvalBaseLLM
print("deepeval", deepeval.__version__)
print("--- DeepEvalBaseLLM")
print(inspect.getsource(DeepEvalBaseLLM)[:3500])
from deepeval.metrics import AnswerRelevancyMetric, GEval
print("--- AnswerRelevancyMetric.__init__"); print(inspect.signature(AnswerRelevancyMetric.__init__))
print("--- GEval.__init__"); print(inspect.signature(GEval.__init__))
