#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MS-Agent 技能执行器

基于 msagent 库的技能执行实现。

依赖安装：
pip install msagent

MS-Agent 特性：
- 4级渐进式加载（metadata → SKILL.md → resources → execution）
- LLM 自主规划（分析 SKILL.md 决定执行计划）
- 沙箱隔离（通过 ms-enclave 实现容器隔离）
- 自动依赖管理
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

from .skill_executor_base import SkillExecutor, ExecutionStep, SkillExecutorException


logger = logging.getLogger(__name__)

# 检查 MS-Agent 可用性
try:
    from ms_agent.executor import ScriptExecutor
    from ms_agent.skill import Skill
    from ms_agent.enclave import MSEnclave
    MSAGENT_AVAILABLE = True
    logger.info("MS-Agent library is available")
except ImportError:
    MSAGENT_AVAILABLE = False
    logger.warning("MS-Agent library not installed. Install with: pip install ms-agent")
    # 创建占位符类以避免导入错误
    class ScriptExecutor:
        pass
    class Skill:
        pass
    class MSEnclave:
        pass


class MSAgentSkillExecutor(SkillExecutor):
    """
    基于 MS-Agent 库的技能执行器

    特点：
    - 使用 MS-Agent 的 ScriptExecutor 执行脚本
    - 支持 LLM 自主规划工作流
    - 可选沙箱隔离（通过 ms-enclave）
    - 自动管理依赖

    优势：
    - LLM 自主分析 SKILL.md，智能规划执行步骤
    - 进程内执行，无 subprocess 开销
    - 支持沙箱隔离（安全）
    - 统一的工具调用接口

    劣势：
    - 需要额外依赖 msagent
    - 需要 LLM 调用（额外成本）
    - 配置较复杂

    配置：
        use_sandbox: 是否使用沙箱隔离（需要 Docker）
        llm_model: 用于规划的 LLM 模型
    """

    def __init__(
        self,
        skill_dir: Path,
        timeout: int = 30,
        use_sandbox: bool = False,
        llm_model: Optional[str] = None
    ):
        super().__init__(skill_dir)

        if not MSAGENT_AVAILABLE:
            raise SkillExecutorException(
                "MS-Agent library is not installed. "
                "Install it with: pip install msagent"
            )

        self.timeout = timeout
        self.use_sandbox = use_sandbox
        self.llm_model = llm_model

        # 初始化 MS-Agent 组件
        self._init_msagent_components()

    def _init_msagent_components(self):
        """初始化 MS-Agent 组件"""
        try:
            # 创建 Skill 对象
            self.skill = Skill.from_directory(self.skill_dir)
            logger.debug(f"Loaded MS-Agent skill from {self.skill_dir}")

            # 创建 ScriptExecutor
            self.script_executor = ScriptExecutor(
                skill=self.skill,
                timeout=self.timeout
            )

            # 创建沙箱（如果启用）
            if self.use_sandbox:
                try:
                    self.enclave = MSEnclave()
                    logger.info("MS-Agent sandbox (ms-enclave) initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize ms-enclave, falling back to non-sandbox mode: {e}")
                    self.enclave = None
                    self.use_sandbox = False
            else:
                self.enclave = None

        except Exception as e:
            raise SkillExecutorException(f"Failed to initialize MS-Agent components: {e}")

    def parse_workflow(self) -> List[ExecutionStep]:
        """
        解析 SKILL.md 工作流

        MS-Agent 使用 LLM 自主分析 SKILL.md，这里返回原始步骤用于信息展示。
        实际执行时，MS-Agent 会自主规划执行顺序和方式。
        """
        if not self.skill_md.exists():
            raise SkillExecutorException(f"SKILL.md not found: {self.skill_md}")

        # 从 MS-Agent Skill 对象获取步骤
        # MS-Agent 的步骤结构可能不同，这里做适配
        steps = []

        try:
            # 尝试从 skill 对象获取预定义的步骤
            if hasattr(self.skill, 'steps') and self.skill.steps:
                for idx, step_def in enumerate(self.skill.steps, 1):
                    steps.append(ExecutionStep(
                        step_number=idx,
                        title=step_def.get('title', f'Step {idx}'),
                        command=step_def.get('command', ''),
                        script_path=Path(step_def['script']) if 'script' in step_def else None,
                        args=step_def.get('args', [])
                    ))
            else:
                # 如果没有预定义步骤，使用标准解析器
                from .skill_md_executor import SkillWorkflowParser
                parser = SkillWorkflowParser(self.skill_md)
                steps_data = parser.parse_execution_steps()

                for step_data in steps_data:
                    steps.append(ExecutionStep(
                        step_number=step_data.step_number,
                        title=step_data.title,
                        command=step_data.command,
                        script_path=step_data.script_path,
                        args=step_data.args
                    ))

        except Exception as e:
            logger.warning(f"Failed to parse workflow with MS-Agent: {e}, using fallback parser")
            # 回退到标准解析
            from .skill_md_executor import SkillWorkflowParser
            parser = SkillWorkflowParser(self.skill_md)
            steps_data = parser.parse_execution_steps()

            for step_data in steps_data:
                steps.append(ExecutionStep(
                    step_number=step_data.step_number,
                    title=step_data.title,
                    command=step_data.command,
                    script_path=step_data.script_path,
                    args=step_data.args
                ))

        return steps

    def execute_step(
        self,
        step: ExecutionStep,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        注意：MS-Agent 通常执行完整工作流，单个步骤执行主要用于兼容性接口。
        """
        if not step.script_path:
            return {
                "step": step.step_number,
                "title": step.title,
                "status": "skipped",
                "message": "No script to execute"
            }

        script_full_path = self.scripts_dir / step.script_path

        if not script_full_path.exists():
            return {
                "step": step.step_number,
                "title": step.title,
                "status": "error",
                "error": f"Script not found: {script_full_path}"
            }

        try:
            # 使用 MS-Agent ScriptExecutor 执行
            if self.use_sandbox and self.enclave:
                # 在沙箱中执行
                result = self.enclave.execute_script(
                    script=str(script_full_path),
                    input_data=input_data,
                    timeout=self.timeout
                )
            else:
                # 直接执行（进程内）
                result = self.script_executor.execute_script(
                    script=str(script_full_path),
                    input_data=input_data
                )

            return {
                "step": step.step_number,
                "title": step.title,
                "status": "success",
                "output": result
            }

        except Exception as e:
            return {
                "step": step.step_number,
                "title": step.title,
                "status": "error",
                "error": str(e)
            }

    async def execute(
        self,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行完整工作流

        MS-Agent 的核心优势：LLM 自主规划执行
        """
        try:
            # 使用 MS-Agent 的 LLM 规划执行
            if self.use_sandbox and self.enclave:
                # 沙箱模式执行
                result = await asyncio.to_thread(
                    self.enclave.execute_skill,
                    skill=self.skill,
                    input_data=input_data,
                    timeout=self.timeout
                )
            else:
                # 直接模式执行
                result = await asyncio.to_thread(
                    self.script_executor.execute,
                    input_data=input_data
                )

            return {
                "success": True,
                "skill": self.skill_dir.name,
                "backend": self.get_backend_name(),
                "final_output": result,
                "llm_planned": True  # 标记使用了 LLM 规划
            }

        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"MS-Agent execution error: {str(e)}\n{traceback.format_exc()}",
                "backend": self.get_backend_name()
            }

    def get_backend_info(self) -> Dict[str, Any]:
        """获取后端信息"""
        info = super().get_backend_info()
        info.update({
            "msagent_available": MSAGENT_AVAILABLE,
            "use_sandbox": self.use_sandbox,
            "llm_model": self.llm_model,
            "llm_planning": True
        })
        return info
