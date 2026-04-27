#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MS-Agent Sandbox 技能执行器

使用 MS-Agent 的 EnclaveSandbox 进行沙箱隔离的脚本执行。

特点：
- Docker 容器隔离
- 自动安装依赖
- 安全执行环境

依赖：
pip install ms-agent  (从 GitHub 安装)
"""

import logging
import subprocess
import tempfile
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

from .skill_executor_base import SkillExecutor, ExecutionStep, SkillExecutorException


logger = logging.getLogger(__name__)

# 检查 MS-Agent EnclaveSandbox 可用性
try:
    from ms_agent.sandbox import EnclaveSandbox
    SANDBOX_AVAILABLE = True
    logger.info("MS-Agent EnclaveSandbox is available")
except ImportError:
    SANDBOX_AVAILABLE = False
    logger.warning("MS-Agent EnclaveSandbox not installed. Install with: pip install git+https://github.com/modelscope/ms-agent.git")


class MSAgentSandboxExecutor(SkillExecutor):
    """
    使用 MS-Agent EnclaveSandbox 的技能执行器

    特点：
    - Docker 沙箱隔离
    - 自动安装依赖
    - 安全执行环境

    劣势：
    - 需要 Docker 运行
    - 容器启动开销
    - 依赖环境配置

    优势：
    - 完全隔离的执行环境
    - 自动依赖管理
    - 安全性更高
    """

    def __init__(self, skill_dir: Path, timeout: int = 30, docker_image: str = "python:3.11-slim"):
        super().__init__(skill_dir)
        self.timeout = timeout
        self.docker_image = docker_image

        if not SANDBOX_AVAILABLE:
            raise SkillExecutorException(
                "MS-Agent EnclaveSandbox not installed. "
                "Install with: pip install git+https://github.com/modelscope/ms-agent.git"
            )

    def parse_workflow(self) -> List[ExecutionStep]:
        """解析 SKILL.md 工作流"""
        # 复用 subprocess executor 的解析逻辑
        from .skill_md_executor import SkillWorkflowParser
        from .skill_executor_base import ExecutionStep

        if not self.skill_md.exists():
            raise SkillExecutorException(f"SKILL.md not found: {self.skill_md}")

        parser = SkillWorkflowParser(self.skill_md)
        steps_data = parser.parse_execution_steps()

        steps = []
        for step_data in steps_data:
            steps.append(ExecutionStep(
                step_number=step_data.step_number,
                title=step_data.title,
                command=step_data.command,
                script_path=step_data.script_path,
                args=step_data.args
            ))

        return sorted(steps, key=lambda x: x.step_number)

    async def execute_step(
        self,
        step: ExecutionStep,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """执行单个步骤（在沙箱中）"""
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
            # 创建沙箱实例
            sandbox = EnclaveSandbox(image=self.docker_image)

            # 读取脚本内容
            script_content = script_full_path.read_text(encoding='utf-8')

            # 构建执行代码
            exec_code = f"""
import json
import sys

# 输入数据
input_data = {json.dumps(input_data, ensure_ascii=False)}

# 执行脚本
{self._build_script_execution_code(step, script_full_path)}
"""

            # 在沙箱中执行
            result = await sandbox.async_execute(python_code=exec_code)

            if result.get("status") == "success":
                # 解析输出
                try:
                    output = json.loads(result.get("output", "{}"))
                    return {
                        "step": step.step_number,
                        "title": step.title,
                        "status": "success",
                        "output": output,
                        "backend": "msagent-sandbox"
                    }
                except json.JSONDecodeError:
                    return {
                        "step": step.step_number,
                        "title": step.title,
                        "status": "success",
                        "output": result.get("output", ""),
                        "backend": "msagent-sandbox"
                    }
            else:
                return {
                    "step": step.step_number,
                    "title": step.title,
                    "status": "error",
                    "error": result.get("error", "Unknown sandbox error"),
                    "backend": "msagent-sandbox"
                }

        except Exception as e:
            import traceback
            return {
                "step": step.step_number,
                "title": step.title,
                "status": "error",
                "error": f"Sandbox execution error: {str(e)}",
                "traceback": traceback.format_exc(),
                "backend": "msagent-sandbox"
            }

    def _build_script_execution_code(self, step: ExecutionStep, script_path: Path) -> str:
        """构建脚本执行代码"""
        # 读取脚本内容
        script_content = script_path.read_text(encoding='utf-8')

        # 提取脚本的主执行逻辑
        # 这是一个简化版本 - 实际使用时可能需要更复杂的处理

        return f"""
# 执行 {step.script_path}
# 原始脚本内容:

{script_content}

# 注意：沙箱环境中需要手动处理输入参数
"""

    async def execute(
        self,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """执行完整工作流"""
        try:
            steps = self.parse_workflow()

            if not steps:
                return {
                    "success": False,
                    "error": "No execution steps found in SKILL.md",
                    "backend": self.get_backend_name()
                }

            results = {
                "success": True,
                "skill": self.skill_dir.name,
                "backend": self.get_backend_name(),
                "steps_executed": len(steps),
                "step_results": [],
                "final_output": None
            }

            current_data = input_data

            for step in steps:
                step_result = await self.execute_step(step, current_data, env)
                results["step_results"].append(step_result)

                if step_result["status"] == "error":
                    results["success"] = False
                    results["error"] = f"Step {step.step_number} ({step.title}) failed: {step_result.get('error', 'Unknown error')}"
                    break

                # 将当前步骤的输出作为下一步的输入
                if "output" in step_result:
                    if isinstance(step_result["output"], dict):
                        output_to_merge = step_result["output"].copy()
                        if "data" in output_to_merge and isinstance(output_to_merge["data"], dict):
                            data_contents = output_to_merge.pop("data")
                            for key, value in data_contents.items():
                                output_to_merge[key] = value

                        current_data = {
                            **input_data,
                            **output_to_merge
                        }
                    else:
                        current_data = {
                            **input_data,
                            "output": step_result["output"]
                        }

            # 最后一步的输出作为最终输出
            if results["step_results"]:
                last_step = results["step_results"][-1]
                if last_step["status"] == "success" and "output" in last_step:
                    results["final_output"] = last_step["output"]
                elif "error" in last_step:
                    results["error"] = last_step["error"]

            return results

        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"Workflow execution error: {str(e)}\n{traceback.format_exc()}",
                "backend": self.get_backend_name()
            }

    def get_backend_info(self) -> Dict[str, Any]:
        """获取后端信息"""
        info = super().get_backend_info()
        info.update({
            "msagent_available": True,
            "sandbox_available": SANDBOX_AVAILABLE,
            "docker_image": self.docker_image,
            "requires_docker": True
        })
        return info


def get_sandbox_status() -> Dict[str, Any]:
    """获取沙箱状态"""
    if not SANDBOX_AVAILABLE:
        return {
            "available": False,
            "reason": "MS-Agent not installed"
        }

    # 检查 Docker
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5
        )
        docker_available = result.returncode == 0
    except:
        docker_available = False

    return {
        "available": SANDBOX_AVAILABLE,
        "docker_available": docker_available,
        "docker_required": True
    }
