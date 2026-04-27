#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Subprocess 技能执行器

基于 subprocess.run() 的脚本执行实现。
这是当前项目的默认执行方式。
"""

import logging
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from .skill_executor_base import SkillExecutor, ExecutionStep, SkillExecutorException
from .skill_md_executor import SkillWorkflowParser


logger = logging.getLogger(__name__)


class SubprocessSkillExecutor(SkillExecutor):
    """
    基于 subprocess 的技能执行器

    特点：
    - 直接调用 Python 解释器执行脚本
    - 通过临时文件传递输入数据
    - 解析脚本的标准输出获取结果
    - 每个步骤独立执行，通过 JSON 数据串联

    优势：
    - 实现简单，无额外依赖
    - 脚本间隔离性好
    - 易于调试（可直接运行脚本）

    劣势：
    - 进程启动开销
    - 无沙箱隔离
    - 无 LLM 自主规划能力
    """

    def __init__(self, skill_dir: Path, timeout: int = 30):
        super().__init__(skill_dir)
        self.timeout = timeout

    def parse_workflow(self) -> List[ExecutionStep]:
        """解析 SKILL.md 工作流"""
        if not self.skill_md.exists():
            raise SkillExecutorException(f"SKILL.md not found: {self.skill_md}")

        parser = SkillWorkflowParser(self.skill_md)
        steps_data = parser.parse_execution_steps()

        # 转换为通用 ExecutionStep 格式
        steps = []
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
        """执行单个步骤"""
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

        # 创建临时输入文件
        temp_input = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        )

        try:
            # 替换参数中的占位符
            processed_args = self._process_args(step.args, input_data, temp_input.name)

            # 写入输入数据
            json.dump(input_data, temp_input, ensure_ascii=False, indent=2)
            temp_input.close()

            # 构建命令
            cmd = [
                'python',
                str(script_full_path.absolute()),
                '--input',
                temp_input.name
            ]

            # 添加已知安全的标志及其值
            skip_next = False
            for i, arg in enumerate(processed_args):
                if skip_next:
                    skip_next = False
                    continue

                # 跳过 --input 及其值
                if arg == '--input':
                    skip_next = True
                    continue

                # 跳过 --output 及其值
                if arg == '--output':
                    skip_next = True
                    continue

                # 跳过占位符
                if arg.startswith('<') or any(ord(c) > 127 for c in arg):
                    continue

                # 对于其他 -- 参数，添加它和它的值
                if arg.startswith('--'):
                    cmd.append(arg)
                    if i + 1 < len(processed_args) and not processed_args[i + 1].startswith('--'):
                        cmd.append(processed_args[i + 1])
                        skip_next = True

            # 执行脚本
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(script_full_path.parent.absolute()),
                env=env or {},
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    return {
                        "step": step.step_number,
                        "title": step.title,
                        "status": "success",
                        "output": output
                    }
                except json.JSONDecodeError:
                    return {
                        "step": step.step_number,
                        "title": step.title,
                        "status": "success",
                        "output": result.stdout
                    }
            else:
                return {
                    "step": step.step_number,
                    "title": step.title,
                    "status": "error",
                    "error": result.stderr or result.stdout
                }

        except subprocess.TimeoutExpired:
            return {
                "step": step.step_number,
                "title": step.title,
                "status": "error",
                "error": "Execution timeout"
            }
        finally:
            # 清理临时文件
            try:
                Path(temp_input.name).unlink()
            except:
                pass

    async def execute(
        self,
        input_data: Dict[str, Any],
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """执行完整工作流"""
        import asyncio

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
                # 在异步线程中执行
                step_result = await asyncio.to_thread(
                    self.execute_step, step, current_data, env
                )
                results["step_results"].append(step_result)

                if step_result["status"] == "error":
                    results["success"] = False
                    results["error"] = f"Step {step.step_number} ({step.title}) failed: {step_result.get('error', 'Unknown error')}"
                    break

                # 检查 incomplete 状态
                if step_result["status"] == "success" and "output" in step_result:
                    output = step_result["output"]

                    if isinstance(output, dict) and output.get("data", {}).get("status") == "incomplete":
                        results["final_output"] = output
                        results["incomplete"] = True
                        results["message"] = "Incomplete data - requires user input"
                        return results

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

    def _process_args(
        self,
        args: List[str],
        input_data: Dict[str, Any],
        input_file: str
    ) -> List[str]:
        """处理参数，替换占位符"""
        processed = []

        # 占位符映射
        placeholders = {
            '<input_file>': input_file,
            '<健康数据文件>': input_file,
            '<模板名称>': 'report',
            '<API地址>': 'http://localhost:8000',
            '<患者ID>': 'TEST001',
        }

        for arg in args:
            for placeholder, value in placeholders.items():
                arg = arg.replace(placeholder, value)
            processed.append(arg)

        return processed
