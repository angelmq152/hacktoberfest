from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from shared.contracts import OutFile


class ToolError(Exception):
    """Invalid arguments or a failed tool call; the message is safe to show the LLM."""


@dataclass
class ToolContext:
    chat_id: int
    user_id: int
    out_dir: Path                            # per-chat output dir, e.g. /data/out/<chat_id>


@dataclass
class ToolResult:
    data: str                                # text fed back to the LLM (already truncated)
    files: list[OutFile] = field(default_factory=list)


@dataclass
class ToolSpec:
    name: str
    description: str
    params: dict[str, str]                   # arg name -> short description for the prompt
    dangerous: bool                          # True -> requires user confirmation
    validate: Callable[[dict], dict]         # returns cleaned args or raises ToolError
    run: Callable[[dict, ToolContext], Awaitable[ToolResult]]
