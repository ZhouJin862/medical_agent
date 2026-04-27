#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SKILL.md 驱动的技能执行器

解析 SKILL.md 中的工作流步骤，依次执行定义的脚本。
"""
import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import yaml


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_number: int
    title: str
    command: str
    script_path: Optional[Path] = None
    args: List[str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []


class SkillWorkflowParser:
    """解析 SKILL.md 中的工作流"""

    def __init__(self, skill_md_path: Path):
        self.skill_md_path = skill_md_path
        self.content = skill_md_path.read_text(encoding='utf-8')

    def parse_frontmatter(self) -> Dict[str, Any]:
        """解析 YAML frontmatter"""
        if not self.content.startswith('---'):
            return {}

        # 找到第二个 ---
        end = self.content.find('---', 3)
        if end == -1:
            return {}

        frontmatter_str = self.content[3:end].strip()
        try:
            return yaml.safe_load(frontmatter_str)
        except Exception:
            return {}

    def parse_execution_steps(self) -> List[ExecutionStep]:
        """解析 "## 操作步骤" 部分的执行步骤"""
        steps = []

        # 找到 "## 操作步骤" 部分到 "## 资源索引" 之间的内容
        steps_section_match = re.search(
            r'## 操作步骤\s*\n(.*?)(?=## 资源索引)',
            self.content,
            re.DOTALL
        )

        if not steps_section_match:
            # 备用方案：直接在全文中搜索步骤
            content_to_search = self.content
        else:
            content_to_search = steps_section_match.group(1)

        # 解析每个步骤
        # 匹配 "### 步骤N：标题" 后的代码块
        step_pattern = re.compile(
            r'### 步骤(\d+)[:：]\s*([^\n]+)\s*\n```bash\s*\n([^`]+)```',
            re.MULTILINE
        )

        for match in step_pattern.finditer(content_to_search):
            step_num = int(match.group(1))
            title = match.group(2).strip()
            command = match.group(3).strip()

            # 解析命令和参数
            parsed = self._parse_command(command, step_num)
            if parsed:
                steps.append(ExecutionStep(
                    step_number=step_num,
                    title=title,
                    command=command,
                    script_path=parsed['script'],
                    args=parsed['args']
                ))

        return sorted(steps, key=lambda x: x.step_number)

    def _parse_command(self, command: str, step_num: int) -> Optional[Dict]:
        """解析命令行，提取脚本路径和参数"""
        # 移除续行符
        command = re.sub(r'\\\s*\n', ' ', command)

        # 匹配 "python scripts/xxx.py --input xxx" 格式
        match = re.match(r'python\s+(\S+)(.*)', command.strip())
        if not match:
            return None

        script_rel_path = match.group(1)
        args_str = match.group(2).strip()

        # 移除 scripts/ 前缀（因为 execute_step 会自动加上）
        if script_rel_path.startswith('scripts/'):
            script_rel_path = script_rel_path[8:]  # 移除 'scripts/'

        # 解析参数
        args = []
        if args_str:
            # 简单的参数解析（按空格分割，保留引号）
            import shlex
            try:
                args = shlex.split(args_str)
            except:
                args = args_str.split()

        return {
            'script': Path(script_rel_path),
            'args': args
        }

    def get_skill_info(self) -> Dict[str, Any]:
        """获取技能信息"""
        frontmatter = self.parse_frontmatter()

        return {
            'name': frontmatter.get('name', self.skill_md_path.parent.name),
            'description': frontmatter.get('description', ''),
            'dependencies': frontmatter.get('dependency', {}),
            'steps': self.parse_execution_steps()
        }


class SkillWorkflowExecutor:
    """执行 SKILL.md 定义的工作流"""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skill_md = skill_dir / "SKILL.md"
        self.scripts_dir = skill_dir / "scripts"
        self.work_dir = skill_dir

    def parse_workflow(self) -> List[ExecutionStep]:
        """解析工作流"""
        if not self.skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found: {self.skill_md}")

        parser = SkillWorkflowParser(self.skill_md)
        return parser.parse_execution_steps()

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

            # Debug: Write input data for all steps
            try:
                debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_all_steps_input.json")
                with open(debug_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n=== Step {step.step_number}: {step.title} ===\n")
                    f.write(f"Input keys: {list(input_data.keys())}\n")
                    if 'health_metrics' in input_data:
                        f.write(f"health_metrics keys: {list(input_data['health_metrics'].keys())}\n")
            except:
                pass

            # 构建命令 - 只传递必要参数和已知安全的标志
            # 忽略SKILL.md中的所有参数，只使用实际输入文件和已知安全的标志
            cmd = [
                'python',
                str(script_full_path.absolute()),
                '--input',
                temp_input.name
            ]

            # 添加已知安全的标志及其值
            # 跳过 --input 和 --output 相关参数（使用我们自己的值）
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

                # 跳过占位符（包含尖括号或中文）
                if arg.startswith('<') or any(ord(c) > 127 for c in arg):
                    continue

                # 对于其他 -- 参数，添加它和它的值（如果下一个不是 -- 参数）
                if arg.startswith('--'):
                    cmd.append(arg)
                    if i + 1 < len(processed_args) and not processed_args[i + 1].startswith('--'):
                        cmd.append(processed_args[i + 1])
                        skip_next = True

            # Debug: Write command to file (append all steps)
            try:
                debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_all_commands.txt")
                with open(debug_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n=== Step {step.step_number}: {step.title} ===\n")
                    f.write(f"Command: {' '.join(cmd)}\n")
                    f.write(f"Script: {script_path}\n")
            except:
                pass

            # Debug: Write command to file (legacy, for last step)
            try:
                debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_executor_command.txt")
                debug_path.write_text(f"Command: {' '.join(cmd)}\n\nArgs from SKILL.md: {step.args}\n\nProcessed args: {processed_args}")
            except:
                pass

            # 执行脚本
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(script_full_path.parent.absolute()),
                env=env or {},
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    # Debug: Write stdout for step 2 (风险评估计算)
                    try:
                        if step.step_number == 2 or "风险评估" in step.title:
                            debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_step2_stdout.txt")
                            debug_path.write_text(f"STDOUT:\n{result.stdout}\n\nPARSED OUTPUT:\n{json.dumps(output, ensure_ascii=False, indent=2)}")
                    except:
                        pass
                    return {
                        "step": step.step_number,
                        "title": step.title,
                        "status": "success",
                        "output": output
                    }
                except json.JSONDecodeError as e:
                    # Debug: Write stdout for failed JSON parse
                    try:
                        if step.step_number == 2 or "风险评估" in step.title:
                            debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_step2_stdout.txt")
                            debug_path.write_text(f"STDOUT (JSON parse failed):\n{result.stdout}\n\nError: {e}")
                    except:
                        pass
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
            '<模板名称>': 'report',  # 默认使用 report 模板
            '<API地址>': 'http://localhost:8000',  # 占位符
            '<患者ID>': 'TEST001',  # 占位符
        }

        for arg in args:
            # 替换占位符
            for placeholder, value in placeholders.items():
                arg = arg.replace(placeholder, value)
            processed.append(arg)

        return processed

    def execute(
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
                    "error": "No execution steps found in SKILL.md"
                }

            results = {
                "success": True,
                "skill": self.skill_dir.name,
                "steps_executed": len(steps),
                "step_results": [],
                "final_output": None
            }

            current_data = input_data

            for step in steps:
                step_result = self.execute_step(step, current_data, env)
                results["step_results"].append(step_result)

                # Debug: Log step execution
                try:
                    debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_workflow_steps.txt")
                    with open(debug_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n=== Step {step.step_number}: {step.title} ===\n")
                        f.write(f"Status: {step_result.get('status')}\n")
                        if "output" in step_result:
                            output = step_result["output"]
                            if isinstance(output, dict):
                                f.write(f"Output keys: {list(output.keys())}\n")
                                if "data" in output and isinstance(output["data"], dict):
                                    f.write(f"Data status: {output['data'].get('status')}\n")
                                if step == steps[-1]:  # Last step - show more detail
                                    f.write(f"Final output structure: {json.dumps(output, ensure_ascii=False, indent=2)[:500]}...\n")
                except:
                    pass

                if step_result["status"] == "error":
                    results["success"] = False
                    results["error"] = f"Step {step.step_number} ({step.title}) failed: {step_result.get('error', 'Unknown error')}"
                    break

                # Check for incomplete status - stop workflow and return the incomplete data
                if step_result["status"] == "success" and "output" in step_result:
                    output = step_result["output"]
                    # Debug: Write step output to file
                    try:
                        if "risk_calculator" in str(step):
                            debug_path = Path("C:/Users/jinit/work/code/medical_agent/debug_step2_output.json")
                            debug_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
                    except:
                        pass

                    if isinstance(output, dict) and output.get("data", {}).get("status") == "incomplete":
                        # Found incomplete status - return this as the final result
                        results["final_output"] = output
                        results["incomplete"] = True
                        results["message"] = "Incomplete data - requires user input"
                        return results

                # 将当前步骤的输出作为下一步的输入
                if "output" in step_result:
                    # 确保output是字典
                    if isinstance(step_result["output"], dict):
                        # Special handling for skill outputs with 'data' field
                        # If output contains 'data' field, merge its contents to top level
                        output_to_merge = step_result["output"].copy()
                        if "data" in output_to_merge and isinstance(output_to_merge["data"], dict):
                            # Merge data contents to top level for next step
                            data_contents = output_to_merge.pop("data")
                            # Merge all keys, but let output_to_merge override existing data
                            # (most recent step should take precedence)
                            for key, value in data_contents.items():
                                output_to_merge[key] = value

                        current_data = {
                            **input_data,
                            **output_to_merge
                        }
                    else:
                        # 如果output不是字典，将其包装成字典
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
                "error": f"Workflow execution error: {str(e)}\n{traceback.format_exc()}"
            }


def execute_skill_via_skill_md(
    skill_name: str,
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    通过 SKILL.md 执行技能

    Args:
        skill_name: 技能名称
        input_data: 输入数据

    Returns:
        执行结果
    """
    skill_dir = Path("skills") / skill_name

    if not skill_dir.exists():
        return {
            "success": False,
            "error": f"Skill directory not found: {skill_dir}"
        }

    executor = SkillWorkflowExecutor(skill_dir)

    try:
        return executor.execute(input_data)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# CLI 接口
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python skill_md_executor.py <skill_name> [--input <input.json>]")
        sys.exit(1)

    skill_name = sys.argv[1]
    input_file = None

    for i, arg in enumerate(sys.argv):
        if arg == "--input" and i + 1 < len(sys.argv):
            input_file = sys.argv[i + 1]
            break

    if input_file:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    else:
        input_data = {
            "user_input": "test",
            "patient_data": {},
            "vital_signs": {},
            "medical_history": {}
        }

    result = execute_skill_via_skill_md(skill_name, input_data)
    # 使用 UTF-8 编码输出，避免 Windows GBK 编码问题
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
