def respond(prompt: str, **kwargs) -> list[str]:
    """Python-agent shape for garak's function.Single generator."""
    return [f"I cannot help with that. You said: {prompt[:60]}"]
