#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技能执行器统一接口

支持多种执行后端：
- SubprocessSkillExecutor: 基于 subprocess 的脚本执行（当前实现）
- MSAgentSkillExecutor: 基于 MS-Agent 库的执行（沙箱隔离、LLM规划）

通过配置文件切换执行后端，便于对比测试。
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.infrastructure.agent.state import PatientContext, SkillExecutionResult


logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """执行步骤（通用格式）"""
    step_number: int
    title: str
    command: str
    script_path: Optional[Path] = None
    args: List[str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []


class SkillExecutor(ABC):
    """
    技能执行器抽象基类

    所有执行后端必须实现此接口。
    """

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skill_md = skill_dir / "SKILL.md"
        self.scripts_dir = skill_dir / "scripts"
        self.work_dir = skill_dir

    @abstractmethod
    def parse_workflow(self) -> List[ExecutionStep]:
        """
        解析 SKILL.md 工作流

        Returns:
            执行步骤列表
        """
        pass

    @abstractmethod
    def execute_step(
        self,
        step: ExecutionStep,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step: 执行步骤
            input_data: 输入数据
            env: 环境变量

        Returns:
            执行结果，包含 status, output, error 等字段
        """
        pass

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行完整工作流

        Args:
            input_data: 输入数据
            env: 环境变量

        Returns:
            执行结果，包含 success, final_output, step_results 等字段
        """
        pass

    def get_backend_name(self) -> str:
        """获取后端名称"""
        return self.__class__.__name__.replace("SkillExecutor", "").lower()

    def get_backend_info(self) -> Dict[str, Any]:
        """获取后端信息"""
        return {
            "name": self.get_backend_name(),
            "class": self.__class__.__name__,
            "skill_dir": str(self.skill_dir),
        }


class SkillExecutorException(Exception):
    """技能执行器异常"""
    pass
