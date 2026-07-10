# 投资 Agent 系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现投资 Agent 系统，支持 LLM 驱动的自主分析和问答交互，可配置关注用户持仓基金。

**Architecture:** 采用 LLM 抽象层设计，支持 OpenAI/Anthropic 双 provider；Agent Core 负责对话管理和工具调用循环；自主模式定时触发分析链路，问答模式实时响应用户问题；用户持仓从代码配置，分析数据从数据库读取。

**Tech Stack:** Python, anthropic SDK, openai SDK, FastAPI, PostgreSQL (async), Vue 3, Element Plus

---

## 文件结构

```
backend/app/
├── agent/                          # Agent 模块（新增）
│   ├── __init__.py
│   ├── core.py                     # Agent Core：对话管理 + 工具调用循环
│   ├── service.py                  # Agent Service：自主/问答模式
│   ├── config.py                   # Agent 配置（provider 选择、model）
│   ├── providers/                  # LLM 提供商（新增）
│   │   ├── __init__.py
│   │   ├── base.py                 # Provider 基础接口
│   │   ├── anthropic_provider.py   # Claude API
│   │   ├── openai_provider.py      # OpenAI API
│   │   └── factory.py              # Provider 工厂
│   └── tools/                      # 工具系统（新增）
│       ├── __init__.py
│       ├── registry.py             # 工具注册表
│       ├── definitions.py          # 工具定义（JSON Schema）
│       └── executor.py             # 工具执行器
├── config/
│   └── portfolio.py                # 用户持仓配置（新增）
├── models/
│   ├── fund.py                     # 现有
│   ├── market.py                   # 现有
│   └── agent.py                    # Agent 模型（新增）
└── api/
    └── agent.py                    # Agent API 路由（新增）

frontend/src/
└── views/
    └── AgentSettings.vue           # Agent 设置页面（新增）

backend/
├── .env.example                    # 更新：添加 LLM 配置
├── requirements.txt                # 更新：添加依赖
└── pyproject.toml                  # 更新：添加依赖
```

---

## Task 1: 数据库模型 - Agent 设置与分析历史

**Files:**
- Create: `backend/app/models/agent.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 Agent 模型**

创建 `backend/app/models/agent.py`：

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.utils.db import Base


class AgentSettings(Base):
    """Agent 设置"""
    __tablename__ = "agent_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)  # 设置键
    value = Column(Text, nullable=False)  # 设置值（JSON 字符串）
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentAnalysis(Base):
    """Agent 分析历史"""
    __tablename__ = "agent_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_type = Column(String(20), nullable=False)  # autonomous / interactive
    fund_code = Column(String(10))  # 分析的基金代码（可为空）
    created_at = Column(DateTime, default=func.now())
    
    # 分析输入（工具调用记录）
    tool_calls = Column(JSON)  # 工具调用列表
    
    # 分析输出
    summary = Column(Text)  # 摘要
    reasoning = Column(Text)  # 推理过程
    recommendations = Column(JSON)  # 建议列表
    
    # 元数据
    llm_provider = Column(String(20))  # 使用的 LLM provider
    llm_model = Column(String(50))  # 使用的模型
    duration_seconds = Column(Integer)  # 耗时
```

- [ ] **Step 2: 更新 models __init__.py**

修改 `backend/app/models/__init__.py`：

```python
from app.models.fund import Fund
from app.models.market import IndexDaily, FundFlow
from app.models.advice import AdviceRecord
from app.models.agent import AgentSettings, AgentAnalysis

__all__ = [
    "Fund", 
    "IndexDaily", 
    "FundFlow", 
    "AdviceRecord",
    "AgentSettings",
    "AgentAnalysis",
]
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/models/agent.py backend/app/models/__init__.py
git commit -m "feat: 添加 Agent 数据库模型

- AgentSettings: 存储 agent 配置（开关、provider 等）
- AgentAnalysis: 存储分析历史（输入/输出/耗时）"
```

---

## Task 2: 用户持仓配置

**Files:**
- Create: `backend/app/config/portfolio.py`

- [ ] **Step 1: 创建持仓配置**

创建 `backend/app/config/portfolio.py`：

```python
"""
用户持仓配置

在此文件中配置你关注的基金列表。
Agent 会优先分析这些基金。
"""

# 用户持仓基金列表
USER_PORTFOLIO = [
    {"code": "005827", "name": "易方达蓝筹精选混合", "weight": 0.3},
    {"code": "110011", "name": "易方达中小盘混合", "weight": 0.2},
    {"code": "161725", "name": "招商中证白酒指数", "weight": 0.2},
    {"code": "003834", "name": "华夏能源革新股票", "weight": 0.15},
    {"code": "005612", "name": "中欧医疗健康混合", "weight": 0.15},
]


def get_portfolio_codes():
    """获取持仓基金代码列表"""
    return [fund["code"] for fund in USER_PORTFOLIO]


def get_portfolio_weights():
    """获取持仓基金权重"""
    return {fund["code"]: fund["weight"] for fund in USER_PORTFOLIO}


def get_portfolio_info():
    """获取完整持仓信息"""
    return USER_PORTFOLIO
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/config/portfolio.py
git commit -m "feat: 添加用户持仓配置

- USER_PORTFOLIO: 配置关注的基金列表
- 提供便捷函数获取代码/权重"
```

---

## Task 3: LLM Provider 抽象层

**Files:**
- Create: `backend/app/agent/providers/base.py`
- Create: `backend/app/agent/providers/anthropic_provider.py`
- Create: `backend/app/agent/providers/openai_provider.py`
- Create: `backend/app/agent/providers/factory.py`
- Create: `backend/app/agent/providers/__init__.py`

- [ ] **Step 1: 创建 Provider 基础接口**

创建 `backend/app/agent/providers/base.py`：

```python
"""
LLM Provider 基础接口

所有 LLM 提供商必须实现此接口。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: Optional[str] = None  # 最终回答
    tool_calls: Optional[List[ToolCall]] = None  # 工具调用列表
    usage: Optional[Dict[str, int]] = None  # token 使用统计


class BaseLLMProvider(ABC):
    """LLM Provider 基础类"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """
        发送聊天请求
        
        Args:
            messages: 对话历史 [{"role": "user/assistant", "content": "..."}]
            tools: 工具定义列表（JSON Schema 格式）
            max_tokens: 最大 token 数
        
        Returns:
            LLMResponse: 包含 content 或 tool_calls
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取 provider 名称"""
        pass
```

- [ ] **Step 2: 实现 Anthropic Provider**

创建 `backend/app/agent/providers/anthropic_provider.py`：

```python
"""
Anthropic Claude Provider
"""
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API"""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key, model)
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000
    ) -> LLMResponse:
        # 转换工具格式（Anthropic 使用不同的 schema）
        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema", {})
                }
                for tool in tools
            ]
        
        # 调用 API
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            tools=anthropic_tools
        )
        
        # 解析响应
        content = None
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )
    
    def get_provider_name(self) -> str:
        return "anthropic"
```

- [ ] **Step 3: 实现 OpenAI Provider**

创建 `backend/app/agent/providers/openai_provider.py`：

```python
"""
OpenAI GPT Provider
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT API"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4000
    ) -> LLMResponse:
        # 转换工具格式（OpenAI 使用 function calling）
        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                }
                for tool in tools
            ]
        
        # 调用 API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools,
            max_tokens=max_tokens
        )
        
        # 解析响应
        choice = response.choices[0]
        content = choice.message.content
        tool_calls = []
        
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                import json
                tool_calls.append(ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments)
                ))
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        )
    
    def get_provider_name(self) -> str:
        return "openai"
```

- [ ] **Step 4: 创建 Provider 工厂**

创建 `backend/app/agent/providers/factory.py`：

```python
"""
LLM Provider 工厂
"""
from app.agent.providers.base import BaseLLMProvider
from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.openai_provider import OpenAIProvider
from app.config import settings


def create_provider() -> BaseLLMProvider:
    """根据配置创建 LLM Provider"""
    provider_name = getattr(settings, 'LLM_PROVIDER', 'anthropic')
    
    if provider_name == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY
        model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
        return AnthropicProvider(api_key, model)
    
    elif provider_name == "openai":
        api_key = settings.OPENAI_API_KEY
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview')
        return OpenAIProvider(api_key, model)
    
    else:
        raise ValueError(f"未知的 LLM provider: {provider_name}")
```

- [ ] **Step 5: 创建 __init__.py**

创建 `backend/app/agent/providers/__init__.py`：

```python
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall
from app.agent.providers.factory import create_provider

__all__ = ["BaseLLMProvider", "LLMResponse", "ToolCall", "create_provider"]
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/agent/providers/
git commit -m "feat: 实现 LLM Provider 抽象层

- 定义 BaseLLMProvider 接口
- 实现 AnthropicProvider (Claude)
- 实现 OpenAIProvider (GPT)
- 创建 Provider 工厂，根据配置选择"
```

---

## Task 4: 工具系统 - 定义与执行

**Files:**
- Create: `backend/app/agent/tools/definitions.py`
- Create: `backend/app/agent/tools/executor.py`
- Create: `backend/app/agent/tools/registry.py`
- Create: `backend/app/agent/tools/__init__.py`

- [ ] **Step 1: 定义工具 Schema**

创建 `backend/app/agent/tools/definitions.py`：

```python
"""
工具定义（JSON Schema）

所有可供 Agent 调用的工具都在这里定义。
"""

TOOL_DEFINITIONS = [
    {
        "name": "get_index_data",
        "description": "获取指数历史行情数据（K线）",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_code": {
                    "type": "string",
                    "description": "指数代码，如 000001（上证）、399001（深证）、399006（创业板）"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天数据，默认 30"
                }
            },
            "required": ["index_code"]
        }
    },
    {
        "name": "get_fund_nav",
        "description": "获取基金历史净值数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，如 005827"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天数据，默认 30"
                }
            },
            "required": ["fund_code"]
        }
    },
    {
        "name": "get_fund_info",
        "description": "获取基金基本信息（名称、类型等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码"
                }
            },
            "required": ["fund_code"]
        }
    },
    {
        "name": "analyze_technical",
        "description": "对行情数据做技术分析，返回趋势、支撑压力位、买卖信号",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "K线数据，每条包含 date/open/high/low/close/volume",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": ["data"]
        }
    },
    {
        "name": "get_fund_flow",
        "description": "获取北向资金历史数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天数据，默认 30"
                }
            }
        }
    }
]


def get_tool_definitions() -> list:
    """获取所有工具定义"""
    return TOOL_DEFINITIONS
```

- [ ] **Step 2: 实现工具执行器**

创建 `backend/app/agent/tools/executor.py`：

```python
"""
工具执行器

负责执行 Agent 的工具调用。
"""
import asyncio
from typing import Dict, Any
from app.services.data_collector.akshare_source import AkShareSource
from app.services.analyzer.technical import TechnicalAnalyzer
import pandas as pd


async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数
    
    Returns:
        Dict: 包含 status 和 result/error
    """
    try:
        if tool_name == "get_index_data":
            source = AkShareSource()
            data = await asyncio.to_thread(
                source.get_index_daily,
                tool_input["index_code"],
                tool_input.get("days", 30)
            )
            return {"status": "success", "data": data, "count": len(data)}
        
        elif tool_name == "get_fund_nav":
            source = AkShareSource()
            data = await asyncio.to_thread(
                source.get_fund_nav,
                tool_input["fund_code"],
                tool_input.get("days", 30)
            )
            return {"status": "success", "data": data, "count": len(data)}
        
        elif tool_name == "get_fund_info":
            source = AkShareSource()
            info = await asyncio.to_thread(
                source.get_fund_info,
                tool_input["fund_code"]
            )
            return {"status": "success", "data": info}
        
        elif tool_name == "analyze_technical":
            df = pd.DataFrame(tool_input["data"])
            analyzer = TechnicalAnalyzer()
            result = analyzer.analyze(df)
            return {
                "status": "success",
                "data": {
                    "signal": result.signal,
                    "confidence": result.confidence,
                    "score": result.score,
                    "reasons": result.reasons
                }
            }
        
        elif tool_name == "get_fund_flow":
            source = AkShareSource()
            data = await asyncio.to_thread(
                source.get_fund_flow,
                tool_input.get("days", 30)
            )
            return {"status": "success", "data": data, "count": len(data)}
        
        else:
            return {"status": "error", "error": f"未知工具: {tool_name}"}
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

- [ ] **Step 3: 创建工具注册表**

创建 `backend/app/agent/tools/registry.py`：

```python
"""
工具注册表

管理所有可用工具。
"""
from app.agent.tools.definitions import get_tool_definitions
from app.agent.tools.executor import execute_tool


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools = get_tool_definitions()
    
    def get_definitions(self) -> list:
        """获取所有工具定义"""
        return self.tools
    
    async def execute(self, tool_name: str, tool_input: dict) -> dict:
        """执行工具"""
        return await execute_tool(tool_name, tool_input)


# 全局工具注册表实例
tool_registry = ToolRegistry()
```

- [ ] **Step 4: 创建 __init__.py**

创建 `backend/app/agent/tools/__init__.py`：

```python
from app.agent.tools.registry import tool_registry

__all__ = ["tool_registry"]
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/agent/tools/
git commit -m "feat: 实现工具系统

- 定义工具 JSON Schema（get_index_data, get_fund_nav, analyze_technical 等）
- 实现工具执行器，调用现有数据采集和分析函数
- 创建工具注册表，统一管理"
```

---

## Task 5: Agent Core - 对话管理与工具调用循环

**Files:**
- Create: `backend/app/agent/core.py`
- Create: `backend/app/agent/__init__.py`

- [ ] **Step 1: 实现 Agent Core**

创建 `backend/app/agent/core.py`：

```python
"""
Agent Core

负责对话管理和工具调用循环。
"""
from typing import List, Dict, Any
from app.agent.providers import create_provider, LLMResponse
from app.agent.tools import tool_registry
import json


class AgentCore:
    """Agent 核心"""
    
    def __init__(self):
        self.llm = create_provider()
        self.tools = tool_registry
        self.conversation: List[Dict[str, str]] = []
    
    async def run(self, user_input: str) -> str:
        """
        运行 Agent（工具调用循环）
        
        Args:
            user_input: 用户输入
        
        Returns:
            str: Agent 最终回答
        """
        # 添加用户消息
        self.conversation.append({"role": "user", "content": user_input})
        
        max_iterations = 10  # 防止无限循环
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # 调用 LLM
            response = await self.llm.chat(
                messages=self.conversation,
                tools=self.tools.get_definitions()
            )
            
            # 检查是否需要调用工具
            if response.tool_calls:
                # 添加 assistant 消息（包含工具调用）
                self.conversation.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # 执行所有工具调用
                for tool_call in response.tool_calls:
                    result = await self.tools.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    
                    # 添加工具结果
                    self.conversation.append({
                        "role": "user",
                        "content": f"工具 {tool_call.name} 返回: {json.dumps(result, ensure_ascii=False, default=str)}"
                    })
            
            else:
                # 没有工具调用，返回最终回答
                if response.content:
                    self.conversation.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    return response.content
        
        return "抱歉，分析过程中遇到错误，请稍后重试。"
    
    def reset(self):
        """重置对话历史"""
        self.conversation = []
    
    def get_conversation(self) -> List[Dict[str, str]]:
        """获取当前对话历史"""
        return self.conversation.copy()
```

- [ ] **Step 2: 创建 __init__.py**

创建 `backend/app/agent/__init__.py`：

```python
from app.agent.core import AgentCore

__all__ = ["AgentCore"]
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/agent/core.py backend/app/agent/__init__.py
git commit -m "feat: 实现 Agent Core

- 对话管理（维护 conversation history）
- 工具调用循环（最多 10 次迭代）
- 支持工具结果回传 LLM"
```

---

## Task 6: Agent Service - 自主与问答模式

**Files:**
- Create: `backend/app/agent/service.py`

- [ ] **Step 1: 实现 Agent Service**

创建 `backend/app/agent/service.py`：

```python
"""
Agent Service

提供自主分析和问答交互两种模式。
"""
from datetime import datetime
from app.agent.core import AgentCore
from app.config.portfolio import get_portfolio_codes, get_portfolio_info
from app.models.agent import AgentAnalysis
from app.utils.db import AsyncSessionLocal
from sqlalchemy import select
import json
import time


class AgentService:
    """Agent 服务"""
    
    def __init__(self):
        self.core = AgentCore()
    
    async def analyze_portfolio(self) -> str:
        """
        自主分析模式
        
        分析用户持仓基金，生成投资建议。
        
        Returns:
            str: 分析报告
        """
        start_time = time.time()
        
        # 构建分析提示
        portfolio = get_portfolio_info()
        portfolio_str = "\n".join([
            f"- {fund['code']} ({fund['name']}): 权重 {fund['weight']*100}%"
            for fund in portfolio
        ])
        
        prompt = f"""你是一个专业的投资分析 agent。现在是收盘后，请分析我的持仓基金并给出投资建议。

我的持仓：
{portfolio_str}

请按照以下步骤分析：
1. 获取主要指数（上证、深证、创业板）的近 30 天行情
2. 获取北向资金近 30 天数据
3. 对每只持仓基金：
   - 获取基金信息
   - 获取近 30 天净值
   - 做技术分析
4. 综合分析，生成投资建议

请详细分析每个基金，并给出明确的操作建议（加仓/持有/减仓）和仓位调整建议。
"""
        
        # 运行 Agent
        self.core.reset()
        result = await self.core.run(prompt)
        
        duration = int(time.time() - start_time)
        
        # 保存分析历史
        await self._save_analysis(
            analysis_type="autonomous",
            tool_calls=self.core.get_conversation(),
            summary=result,
            duration_seconds=duration
        )
        
        return result
    
    async def ask_question(self, question: str) -> str:
        """
        问答交互模式
        
        Args:
            question: 用户问题
        
        Returns:
            str: Agent 回答
        """
        start_time = time.time()
        
        # 添加上下文
        portfolio_codes = get_portfolio_codes()
        context_prompt = f"""你是一个专业的投资分析 agent。用户会问你关于投资的问题。

用户关注的基金代码：{', '.join(portfolio_codes)}

请基于实时数据和专业知识回答问题。如果需要使用工具获取数据，请调用相应工具。

用户问题：{question}"""
        
        # 运行 Agent
        self.core.reset()
        result = await self.core.run(context_prompt)
        
        duration = int(time.time() - start_time)
        
        # 保存分析历史
        await self._save_analysis(
            analysis_type="interactive",
            tool_calls=self.core.get_conversation(),
            summary=result,
            duration_seconds=duration
        )
        
        return result
    
    async def _save_analysis(
        self,
        analysis_type: str,
        tool_calls: list,
        summary: str,
        duration_seconds: int
    ):
        """保存分析历史到数据库"""
        async with AsyncSessionLocal() as session:
            analysis = AgentAnalysis(
                analysis_type=analysis_type,
                tool_calls=tool_calls,
                summary=summary,
                llm_provider=self.core.llm.get_provider_name(),
                llm_model=self.core.llm.model,
                duration_seconds=duration_seconds
            )
            session.add(analysis)
            await session.commit()
    
    async def get_latest_analysis(self, limit: int = 10) -> list:
        """获取最新的分析历史"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentAnalysis)
                .order_by(AgentAnalysis.created_at.desc())
                .limit(limit)
            )
            analyses = result.scalars().all()
            
            return [
                {
                    "id": a.id,
                    "type": a.analysis_type,
                    "summary": a.summary,
                    "created_at": str(a.created_at),
                    "duration": a.duration_seconds
                }
                for a in analyses
            ]


# 全局 Agent Service 实例
agent_service = AgentService()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/agent/service.py
git commit -m "feat: 实现 Agent Service

- 自主模式：分析用户持仓，生成投资建议
- 问答模式：回答用户投资问题
- 保存分析历史到数据库"
```

---

## Task 7: Agent API 路由

**Files:**
- Create: `backend/app/api/agent.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 Agent API**

创建 `backend/app/api/agent.py`：

```python
"""
Agent API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.service import agent_service

router = APIRouter(prefix="/agent", tags=["Agent"])


class ChatRequest(BaseModel):
    question: str


@router.post("/analyze")
async def trigger_analysis():
    """触发自主分析"""
    try:
        result = await agent_service.analyze_portfolio()
        return {
            "status": "success",
            "message": "分析完成",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest):
    """问答交互"""
    try:
        result = await agent_service.ask_question(request.question)
        return {
            "status": "success",
            "answer": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(limit: int = 10):
    """获取分析历史"""
    try:
        history = await agent_service.get_latest_analysis(limit)
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: 注册路由到 main.py**

修改 `backend/app/main.py`，在路由注册部分添加：

```python
from app.api import funds, market, advice, tasks, agent

# ... 其他路由注册 ...

app.include_router(agent.router, prefix=settings.API_PREFIX)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/agent.py backend/app/main.py
git commit -m "feat: 实现 Agent API 路由

- POST /api/agent/analyze: 触发自主分析
- POST /api/agent/chat: 问答交互
- GET /api/agent/history: 获取分析历史
- 注册路由到 main.py"
```

---

## Task 8: 配置与依赖

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/requirements.txt`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 更新 .env.example**

在 `backend/.env.example` 中添加：

```bash
# LLM 配置
LLM_PROVIDER=anthropic  # 可选: anthropic / openai

# Anthropic Claude
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
```

- [ ] **Step 2: 更新 requirements.txt**

在 `backend/requirements.txt` 中添加：

```txt
# LLM Providers
anthropic>=0.18.0
openai>=1.12.0
```

- [ ] **Step 3: 更新 pyproject.toml**

在 `backend/pyproject.toml` 的 dependencies 中添加：

```toml
# LLM Providers
"anthropic>=0.18.0",
"openai>=1.12.0",
```

- [ ] **Step 4: 提交**

```bash
git add backend/.env.example backend/requirements.txt backend/pyproject.toml
git commit -m "feat: 添加 LLM 配置和依赖

- .env.example: 添加 LLM provider 配置示例
- requirements.txt: 添加 anthropic 和 openai SDK
- pyproject.toml: 同步更新依赖"
```

---

## Task 9: 前端 Agent 设置页面

**Files:**
- Create: `frontend/src/views/AgentSettings.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: 创建 Agent 设置页面**

创建 `frontend/src/views/AgentSettings.vue`：

```vue
<template>
  <div class="agent-settings">
    <h2>Agent 设置</h2>
    
    <el-card>
      <template #header>
        <div class="card-header">
          <span>自主分析模式</span>
          <el-switch v-model="autoEnabled" @change="toggleAutoMode" />
        </div>
      </template>
      <p>开启后，系统将在每个交易日收盘后自动分析您的持仓基金。</p>
      <p>关闭后，您可以手动点击"立即分析"按钮触发分析。</p>
      <el-button type="primary" @click="triggerAnalysis" :loading="analyzing">
        立即分析
      </el-button>
    </el-card>
    
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>分析历史</span>
      </template>
      <el-table :data="history" stripe>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            {{ row.type === 'autonomous' ? '自主分析' : '问答交互' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="200" />
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration }}秒
          </template>
        </el-table-column>
        <el-table-column label="摘要">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="分析详情" width="80%">
      <pre class="analysis-content">{{ currentAnalysis?.summary }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentApi } from '../api'

const autoEnabled = ref(false)
const analyzing = ref(false)
const history = ref([])
const detailVisible = ref(false)
const currentAnalysis = ref(null)

const toggleAutoMode = async () => {
  // TODO: 调用 API 保存设置
  ElMessage.success(autoEnabled.value ? '已开启自主分析模式' : '已关闭自主分析模式')
}

const triggerAnalysis = async () => {
  analyzing.value = true
  try {
    const { data } = await agentApi.triggerAnalysis()
    ElMessage.success('分析完成')
    await loadHistory()
  } catch (e) {
    ElMessage.error('分析失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    analyzing.value = false
  }
}

const loadHistory = async () => {
  try {
    const { data } = await agentApi.getHistory(10)
    history.value = data.history
  } catch (e) {
    console.error(e)
  }
}

const viewDetail = (analysis) => {
  currentAnalysis.value = analysis
  detailVisible.value = true
}

onMounted(async () => {
  await loadHistory()
})
</script>

<style scoped>
.agent-settings {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.analysis-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  max-height: 600px;
  overflow-y: auto;
}
</style>
```

- [ ] **Step 2: 更新路由**

修改 `frontend/src/router/index.js`，添加：

```javascript
{
  path: '/agent',
  name: 'AgentSettings',
  component: () => import('../views/AgentSettings.vue')
}
```

- [ ] **Step 3: 更新 API**

修改 `frontend/src/api/index.js`，添加：

```javascript
// Agent 相关
export const agentApi = {
  triggerAnalysis: () => api.post('/agent/analyze'),
  chat: (question) => api.post('/agent/chat', { question }),
  getHistory: (limit = 10) => api.get('/agent/history', { params: { limit } })
}
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/AgentSettings.vue frontend/src/router/index.js frontend/src/api/index.js
git commit -m "feat: 实现前端 Agent 设置页面

- 自主模式开关
- 手动触发分析按钮
- 分析历史列表
- 详情对话框"
```

---

## 完成标准

1. ✅ LLM 抽象层支持 OpenAI 和 Anthropic
2. ✅ 工具系统可以调用数据采集和分析函数
3. ✅ Agent Core 支持多轮工具调用
4. ✅ 自主模式可以分析用户持仓
5. ✅ 问答模式可以回答问题
6. ✅ API 接口可用
7. ✅ 前端开关可以触发分析
8. ✅ 分析历史保存到数据库

---

## 后续扩展

1. 实现 Agent 设置持久化（数据库）
2. 添加更多工具（板块分析、估值分析等）
3. 实现分析结果推送（邮件/微信）
4. 优化 prompt 工程，提升分析质量
5. 添加单元测试和集成测试

---

*计划版本：v1.0*  
*创建日期：2026-07-10*
