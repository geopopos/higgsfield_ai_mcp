"""Gemini Video MCP v3.3 package.

Server imports are intentionally lazy so client/orchestrator logic can be tested
without installing the MCP runtime.
"""
__version__ = "3.3.0"

def load_server():
    from .server import mcp, main
    return mcp, main

__all__ = ["__version__", "load_server"]
