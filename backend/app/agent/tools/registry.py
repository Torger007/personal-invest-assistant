"""
工具注册表模块

统一管理工具定义和执行，提供工具查询和执行入口。
"""

from app.agent.tools.definitions import get_tool_definitions, get_tool_definition
from app.agent.tools.executor import execute_tool


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools = get_tool_definitions()

    def get_definitions(self) -> list:
        """获取所有工具定义"""
        return self.tools

    def get_definition(self, tool_name: str) -> dict | None:
        """根据工具名称获取单个工具定义"""
        return get_tool_definition(tool_name)

    def get_tool_names(self) -> list[str]:
        """获取所有已注册的工具名称"""
        return [tool["name"] for tool in self.tools]

    async def execute(self, tool_name: str, tool_input: dict) -> dict:
        """
        执行指定工具

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            dict: 执行结果
        """
        # 验证工具是否存在
        if not self.get_definition(tool_name):
            return {
                "status": "error",
                "error": f"未找到工具: {tool_name}"
            }

        # 执行工具
        return await execute_tool(tool_name, tool_input)


# 全局单例
tool_registry = ToolRegistry()
