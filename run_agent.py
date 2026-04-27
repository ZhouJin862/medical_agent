#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行医疗智能体测试脚本

使用方法:
    python run_agent.py "请帮我做健康评估"
    python run_agent.py --patient-id "patient_001" --query "血压130/85，请评估"
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.agent.graph import MedicalAgent


async def run_agent_test(user_query: str, patient_id: str = "test_patient"):
    """
    运行医疗智能体测试

    Args:
        user_query: 用户查询内容
        patient_id: 患者ID
    """
    print(f"=" * 60)
    print(f"医疗智能体测试")
    print(f"=" * 60)
    print(f"患者ID: {patient_id}")
    print(f"用户查询: {user_query}")
    print(f"-" * 60)

    # 创建智能体
    agent = MedicalAgent()

    # 执行智能体
    print("正在执行智能体...")
    result = await agent.process(
        user_input=user_query,
        patient_id=patient_id
    )

    # 输出结果
    print(f"\n智能体执行结果:")
    print(f"=" * 60)
    print(f"状态: {result.status.value}")
    print(f"意图: {result.intent.value if result.intent else 'N/A'}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"使用的技能: {result.suggested_skill or 'N/A'}")

    if result.executed_skills:
        print(f"\n执行的技能 ({len(result.executed_skills)}):")
        for i, skill in enumerate(result.executed_skills, 1):
            print(f"  {i}. {skill.skill_name}")
            print(f"     成功: {skill.success}")
            print(f"     耗时: {skill.execution_time}ms" if skill.execution_time else "")

    print(f"\n最终响应:")
    print(f"-" * 60)
    # Handle encoding errors for Windows terminal
    try:
        print(result.final_response or "无响应")
    except UnicodeEncodeError:
        print(result.final_response.encode('ascii', 'replace').decode('ascii') or "无响应 (encoding error)")
    print(f"=" * 60)

    # 输出结构化数据（如果有）
    if result.structured_output:
        print(f"\n结构化输出:")
        import json
        print(json.dumps(result.structured_output, ensure_ascii=False, indent=2))

    return result


async def stream_agent_test(user_query: str, patient_id: str = "test_patient"):
    """
    流式输出智能体测试
    """
    print(f"流式输出测试 - {user_query}")
    print("-" * 40)

    agent = MedicalAgent()

    async for state in agent.stream(
        user_input=user_query,
        patient_id=patient_id
    ):
        print(f"状态: {state.status.value}, 步骤: {state.current_step}")
        if state.final_response:
            print(f"响应: {state.final_response[:100]}...")

    print("-" * 40)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行医疗智能体")
    parser.add_argument("--query", "-q", type=str, required=False, help="用户查询内容")
    parser.add_argument("--patient-id", "-p", type=str, default="test_patient", help="患者ID")
    parser.add_argument("--stream", "-s", action="store_true", help="使用流式输出")
    parser.add_argument("--list-skills", "-l", action="store_true", help="列出可用技能")

    args = parser.parse_args()

    # 列出技能
    if args.list_skills:
        print("可用技能:")
        skills_dir = Path("skills")
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    print(f"  - {skill_dir.name}")
                    # 读取技能描述
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        with open(skill_md, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith("# "):
                                    print(f"    {line[2:].strip()}")
                                    break
        return

    # 运行智能体
    if args.stream:
        asyncio.run(stream_agent_test(args.query, args.patient_id))
    else:
        asyncio.run(run_agent_test(args.query, args.patient_id))


if __name__ == "__main__":
    main()
