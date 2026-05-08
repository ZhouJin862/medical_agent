#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SKILL.md Frontmatter Tools 执行器

解析 SKILL.md YAML frontmatter 中的 tools 字段，依次 subprocess 执行定义的脚本。
"""
import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ToolStep:
    """A single tool step parsed from frontmatter."""
    script: str
    args: List[str] = field(default_factory=list)


class SkillToolsExecutor:
    """Execute skills via frontmatter `tools` declarations."""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skill_md = skill_dir / "SKILL.md"

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_tools(self) -> List[ToolStep]:
        """Read SKILL.md frontmatter and return the `tools` list."""
        if not self.skill_md.exists():
            return []

        content = self.skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return []

        end = content.find("---", 3)
        if end == -1:
            return []

        try:
            fm = yaml.safe_load(content[3:end].strip())
        except Exception:
            return []

        if not isinstance(fm, dict) or "tools" not in fm:
            return []

        tools_raw = fm["tools"]
        if not isinstance(tools_raw, list):
            return []

        steps: List[ToolStep] = []
        for entry in tools_raw:
            if not isinstance(entry, dict) or "script" not in entry:
                continue
            steps.append(ToolStep(
                script=entry["script"],
                args=entry.get("args", []),
            ))
        return steps

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run every tool step in order, piping output forward."""
        steps = self.parse_tools()
        if not steps:
            return {
                "success": False,
                "error": "No tools defined in SKILL.md frontmatter",
            }

        results: List[Dict[str, Any]] = []
        current_data = input_data
        prev_output_path: Optional[str] = None
        temp_files: List[str] = []  # track all temp files for cleanup

        try:
            for idx, step in enumerate(steps):
                step_result, prev_output_path = self._execute_step(
                    step=step,
                    step_number=idx + 1,
                    input_data=current_data,
                    prev_output_path=prev_output_path,
                    temp_files=temp_files,
                )
                results.append(step_result)

                if step_result["status"] == "error":
                    return {
                        "success": False,
                        "skill": self.skill_dir.name,
                        "steps_executed": idx + 1,
                        "step_results": results,
                        "error": f"Step {idx + 1} failed: {step_result.get('error', '')}",
                    }

                output = step_result.get("output")

                # Incomplete data – stop pipeline
                if (
                    isinstance(output, dict)
                    and output.get("data", {}).get("status") == "incomplete"
                ):
                    return {
                        "success": True,
                        "skill": self.skill_dir.name,
                        "steps_executed": idx + 1,
                        "step_results": results,
                        "final_output": output,
                        "incomplete": True,
                        "message": "Incomplete data – requires user input",
                    }

                # Pipe data forward
                if isinstance(output, dict):
                    merged = output.copy()
                    if "data" in merged and isinstance(merged["data"], dict):
                        for k, v in merged.pop("data").items():
                            merged[k] = v
                    current_data = {**input_data, **merged}

            # Final output from last step
            final_output = None
            if results and results[-1]["status"] == "success":
                final_output = results[-1].get("output")

            return {
                "success": True,
                "skill": self.skill_dir.name,
                "steps_executed": len(steps),
                "step_results": results,
                "final_output": final_output,
            }
        finally:
            # Clean up all temp files
            for f in temp_files:
                try:
                    Path(f).unlink()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Single step
    # ------------------------------------------------------------------

    def _execute_step(
        self,
        step: ToolStep,
        step_number: int,
        input_data: Dict[str, Any],
        prev_output_path: Optional[str],
        temp_files: List[str],
    ) -> tuple:
        """Execute one tool step.

        Returns (step_result_dict, output_file_path_or_None).
        """
        script_path = self.skill_dir / step.script
        if not script_path.exists():
            return (
                {"step": step_number, "status": "error", "error": f"Script not found: {script_path}"},
                None,
            )

        # Write input data to temp file (for $input)
        tmp_in = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(input_data, tmp_in, ensure_ascii=False, indent=2)
        tmp_in.close()
        temp_files.append(tmp_in.name)

        # Resolve placeholders
        resolved_args = self._resolve_placeholders(
            step.args,
            input_file=tmp_in.name,
            prev_output_file=prev_output_path or tmp_in.name,
            skill_dir=str(self.skill_dir),
        )

        cmd = ["python", str(script_path.resolve())] + resolved_args

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(script_path.parent.resolve()),
                encoding="utf-8",
                errors="replace",
            )

            if proc.returncode == 0:
                try:
                    output = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    output = proc.stdout

                # Write output to temp file for next step's $prev_output
                tmp_out = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                )
                json.dump(
                    output if isinstance(output, dict) else {"raw": output},
                    tmp_out, ensure_ascii=False,
                )
                tmp_out.close()
                temp_files.append(tmp_out.name)

                return (
                    {"step": step_number, "status": "success", "output": output},
                    tmp_out.name,
                )
            else:
                return (
                    {"step": step_number, "status": "error", "error": proc.stderr or proc.stdout},
                    None,
                )

        except subprocess.TimeoutExpired:
            return (
                {"step": step_number, "status": "error", "error": "Execution timeout (30s)"},
                None,
            )
        except Exception as e:
            return (
                {"step": step_number, "status": "error", "error": str(e)},
                None,
            )

    # ------------------------------------------------------------------
    # Placeholder resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_placeholders(
        args: List[str],
        input_file: str,
        prev_output_file: str,
        skill_dir: str,
    ) -> List[str]:
        mapping = {
            "$input": input_file,
            "$prev_output": prev_output_file,
            "$skill_dir": skill_dir,
        }
        resolved = []
        for arg in args:
            for placeholder, value in mapping.items():
                arg = arg.replace(placeholder, value)
            resolved.append(arg)
        return resolved


# ------------------------------------------------------------------
# Top-level helper (used by orchestrator)
# ------------------------------------------------------------------

def execute_skill_via_tools(
    skill_name: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a skill by its frontmatter `tools` declaration."""
    skill_dir = Path("skills") / skill_name
    if not skill_dir.exists():
        return {"success": False, "error": f"Skill directory not found: {skill_dir}"}

    executor = SkillToolsExecutor(skill_dir)
    return executor.execute(input_data)
