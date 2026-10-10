from core.tools.base import ToolSpec
from core.tools.docker_tools import DOCKER_TOOLS
from core.tools.reports import REPORT_TOOLS

TOOLS: dict[str, ToolSpec] = {**DOCKER_TOOLS, **REPORT_TOOLS}
