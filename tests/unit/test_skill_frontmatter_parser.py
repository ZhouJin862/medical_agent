#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试统一SKILL.md格式的解析
"""
import pytest
import tempfile
from pathlib import Path

from src.domain.shared.services.skill_frontmatter_parser import (
    SkillFrontmatterParser,
    validate_skill_frontmatter,
    migrate_legacy_frontmatter,
    generate_skill_template,
)
from src.domain.shared.models.skill_schema import (
    SkillFrontmatter,
    ExecutionType,
    SkillLayer,
    OutputFormat,
)


class TestSkillFrontmatterParser:
    """测试SkillFrontmatterParser"""

    def test_parse_new_format(self):
        """测试解析新格式"""
        # 使用固定路径避免Windows临时目录编码问题
        import os
        temp_dir = Path(tempfile.gettempdir()) / "skill_test"
        temp_dir.mkdir(exist_ok=True)

        test_file = temp_dir / "test_skill.md"

        try:
            content = """---
name: cvd-risk-assessment
display_name: Cardiovascular Risk Assessment
description: Cardiovascular disease risk assessment

version: "1.0.0"
author: test-author
enabled: true

execution_type: workflow
layer: domain
priority: 10

triggers:
  keywords:
    - cvd
    - cardiovascular
    - risk
  confidence_threshold: 0.7

requires:
  python: ">=3.10"
  packages:
    - pyyaml==6.0.1

output:
  format: structured
---
# Skill content here
"""
            # 确保UTF-8编码写入
            test_file.write_text(content, encoding='utf-8')

            parser = SkillFrontmatterParser(strict_mode=False)
            frontmatter, metadata, definition = parser.parse(test_file)

            assert frontmatter is not None
            assert frontmatter.name == "cvd-risk-assessment"
            assert frontmatter.display_name == "Cardiovascular Risk Assessment"
            assert frontmatter.execution_type == ExecutionType.WORKFLOW
            assert frontmatter.layer == SkillLayer.DOMAIN
            assert frontmatter.priority == 10
            assert len(frontmatter.triggers.keywords) == 3
            assert frontmatter.triggers.confidence_threshold == 0.7
            assert len(frontmatter.requires.packages) == 1

            assert metadata is not None
            assert metadata.name == "cvd-risk-assessment"
            assert metadata.layer == SkillLayer.DOMAIN

        finally:
            # 清理
            if test_file.exists():
                test_file.unlink()

    def test_parse_legacy_format(self):
        """测试解析旧格式（向后兼容）"""
        import os
        temp_dir = Path(tempfile.gettempdir()) / "skill_test"
        temp_dir.mkdir(exist_ok=True)

        test_file = temp_dir / "test_legacy.md"

        try:
            # 使用更简单的description避免YAML解析错误
            content = """---
name: hypertension-risk-assessment
description: Hypertension risk assessment
dependency:
  python:
    - pyyaml==6.0.1
    - requests==2.31.0
tags:
  - hypertension
  - blood-pressure
---
# Skill content
"""
            test_file.write_text(content, encoding='utf-8')

            parser = SkillFrontmatterParser(strict_mode=False)
            frontmatter, metadata, _ = parser.parse(test_file)

            assert frontmatter is not None
            assert frontmatter.name == "hypertension-risk-assessment"
            # 应该从tags获取触发词
            assert len(frontmatter.triggers.keywords) >= 2

        finally:
            if test_file.exists():
                test_file.unlink()

    def test_validation_errors(self):
        """测试验证错误检测"""
        import os
        temp_dir = Path(tempfile.gettempdir()) / "skill_test"
        temp_dir.mkdir(exist_ok=True)

        test_file = temp_dir / "test_validation.md"

        try:
            # 缺少必填字段
            content = """---
display_name: Test
---
"""
            test_file.write_text(content, encoding='utf-8')

            parser = SkillFrontmatterParser(strict_mode=False)
            frontmatter, _, _ = parser.parse(test_file)

            # 空frontmatter应该是None（解析失败）
            assert frontmatter is None

        finally:
            if test_file.exists():
                test_file.unlink()

    def test_invalid_name_format(self):
        """测试无效的名称格式"""
        frontmatter = SkillFrontmatter(
            name="Invalid_Name",  # 应该是kebab-case
            description="Test",
        )

        errors = frontmatter.validate()
        assert any("kebab-case" in e for e in errors)


class TestMigration:
    """测试格式迁移"""

    def test_migrate_legacy_to_new(self):
        """测试从旧格式迁移到新格式"""
        legacy = {
            "name": "test-skill",
            "description": "测试技能，触发词：测试、技能",
            "dependency": {
                "python": ["pyyaml==6.0.1"]
            },
            "tags": ["tag1", "tag2"]
        }

        new_frontmatter = migrate_legacy_frontmatter(legacy, "test-skill")

        assert new_frontmatter.name == "test-skill"
        assert new_frontmatter.execution_type == ExecutionType.PROMPT  # 默认
        assert len(new_frontmatter.triggers.keywords) > 0
        assert "测试" in new_frontmatter.triggers.keywords or "技能" in new_frontmatter.triggers.keywords

    def test_keywords_from_description(self):
        """测试从description中提取关键词"""
        description = "评估心血管风险。触发词：心血管、心脏病、中风、风险评估、危险分层"

        keywords = SkillFrontmatter._extract_keywords_from_description(description)

        assert "心血管" in keywords
        assert "心脏病" in keywords
        assert "中风" in keywords


class TestTemplateGeneration:
    """测试模板生成"""

    def test_generate_workflow_template(self):
        """测试生成workflow类型模板"""
        template = generate_skill_template(
            name="test-workflow",
            display_name="测试工作流",
            description="测试工作流技能",
            keywords=["测试", "工作流"],
            execution_type=ExecutionType.WORKFLOW,
        )

        assert "---" in template
        assert "name: test-workflow" in template
        assert "execution_type: workflow" in template
        assert "keywords:" in template

    def test_generate_prompt_template(self):
        """测试生成prompt类型模板"""
        template = generate_skill_template(
            name="test-prompt",
            display_name="测试提示词",
            description="测试提示词技能",
            keywords=["测试", "提示词"],
            execution_type=ExecutionType.PROMPT,
        )

        assert "execution_type: prompt" in template


class TestValidation:
    """测试验证功能"""

    def test_validate_valid_skill(self):
        """测试验证有效的skill"""
        import os
        temp_dir = Path(tempfile.gettempdir()) / "skill_test"
        temp_dir.mkdir(exist_ok=True)

        test_file = temp_dir / "test_valid.md"

        try:
            content = """---
name: valid-skill
description: A valid skill
---
"""
            test_file.write_text(content, encoding='utf-8')

            is_valid, errors = validate_skill_frontmatter(test_file)
            assert is_valid
            assert len(errors) == 0

        finally:
            if test_file.exists():
                test_file.unlink()

    def test_validate_invalid_skill(self):
        """测试验证无效的skill"""
        import os
        temp_dir = Path(tempfile.gettempdir()) / "skill_test"
        temp_dir.mkdir(exist_ok=True)

        test_file = temp_dir / "test_invalid.md"

        try:
            content = """---
# Missing name and description
---
"""
            test_file.write_text(content, encoding='utf-8')

            is_valid, errors = validate_skill_frontmatter(test_file)
            assert not is_valid
            assert len(errors) > 0

        finally:
            if test_file.exists():
                test_file.unlink()


class TestTriggerMatching:
    """测试触发匹配"""

    def test_trigger_keyword_match(self):
        """测试关键词匹配"""
        from src.domain.shared.models.skill_schema import TriggerConfig

        triggers = TriggerConfig(
            keywords=["心血管", "心脏病", "风险评估"],
            intent_patterns=[],
            confidence_threshold=0.7,
        )

        assert triggers.matches("我需要心血管风险评估")
        assert triggers.matches("心脏病要注意什么")
        assert not triggers.matches("头痛怎么办")

    def test_trigger_pattern_match(self):
        """测试正则模式匹配"""
        from src.domain.shared.models.skill_schema import TriggerConfig

        triggers = TriggerConfig(
            keywords=[],
            intent_patterns=[r"评估.*风险", r"检查.*血压"],
            confidence_threshold=0.7,
        )

        assert triggers.matches("请帮我评估心血管风险")
        assert triggers.matches("我想检查一下血压")
        assert not triggers.matches("今天天气怎么样")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
