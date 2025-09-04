class Agent:
    def __init__(self, *args, **kwargs): pass

class Runner: pass

class OpenAIChatCompletionsModel:
    def __init__(self, *args, **kwargs): pass

class AsyncOpenAI:
    def __init__(self, *args, **kwargs): pass

class RunConfig:
    def __init__(self, *args, **kwargs): pass

class RunContextWrapper: pass

class FunctionTool:
    def __init__(self, *args, **kwargs): pass

class GuardrailFunctionOutput:
    def __init__(self, output_info=None, guardrail_function=None, tripwire_triggered=False):
        self.output_info = output_info
        self.guardrail_function = guardrail_function
        self.tripwire_triggered = tripwire_triggered

class InputGuardrail:
    def __init__(self, name=None, guardrail_function=None):
        self.name = name
        self.guardrail_function = guardrail_function

class OutputGuardrail:
    def __init__(self, name=None, guardrail_function=None):
        self.name = name
        self.guardrail_function = guardrail_function



