#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SKILL.md 格式迁移工具

将旧格式的SKILL.md文件迁移到统一的新格式。
"""
import argparse
import re
import shutil
from pathlib import Path
from typing import List, Tuple
import yaml

from src.domain.shared.services.skill_frontmatter_parser import (
    SkillFrontmatterParser,
    migrate_legacy_frontmatter,
    validate_skill_frontmatter,
    generate_skill_template,
)
from src.domain.shared.models.skill_schema import ExecutionType


class SkillMigrationTool:
    """SKILL.md格式迁移工具"""

    def __init__(self, skills_dir: Path, dry_run: bool = False):
        """
        初始化迁移工具。

        Args:
            skills_dir: skills根目录
            dry_run: 是否为演练模式（不实际修改文件）
        """
        self.skills_dir = Path(skills_dir)
        self.dry_run = dry_run
        self.parser = SkillFrontmatterParser(strict_mode=False)
        self.results = {
            "migrated": [],
            "skipped": [],
            "errors": [],
        }

    def migrate_all(self) -> dict:
        """
        迁移所有SKILL.md文件。

        Returns:
            迁移结果统计
        """
        print(f"Scanning skills directory: {self.skills_dir}")

        # 查找所有SKILL.md文件
        skill_files = list(self.skills_dir.rglob("SKILL.md"))

        if not skill_files:
            print("No SKILL.md files found!")
            return self.results

        print(f"Found {len(skill_files)} SKILL.md files")

        for skill_file in skill_files:
            self.migrate_one(skill_file)

        # 打印结果汇总
        self._print_summary()

        return self.results

    def migrate_one(self, skill_file: Path) -> bool:
        """
        迁移单个SKILL.md文件。

        Args:
            skill_file: SKILL.md文件路径

        Returns:
            是否成功迁移
        """
        print(f"\nProcessing: {skill_file.relative_to(self.skills_dir)}")

        try:
            # 读取原文件
            content = skill_file.read_text(encoding='utf-8')

            # 解析现有frontmatter
            frontmatter_dict, body_start = self.parser._parse_frontmatter_yaml(content)

            if not frontmatter_dict:
                print(f"  ⚠️  No frontmatter found, skipping")
                self.results["skipped"].append(str(skill_file))
                return False

            # 检查是否已经是新格式
            if self._is_new_format(frontmatter_dict):
                print(f"  ✓ Already in new format, skipping")
                self.results["skipped"].append(str(skill_file))
                return True

            # 迁移到新格式
            new_frontmatter = migrate_legacy_frontmatter(
                frontmatter_dict,
                skill_file.parent.name
            )

            # 获取body内容
            body_content = content[body_start:] if body_start > 0 else content

            # 生成新文件内容
            new_content = self._generate_new_content(new_frontmatter, body_content)

            # 验证新格式
            if self.dry_run:
                print(f"  [DRY RUN] Would migrate:")
                print(f"    - Old format detected")
                print(f"    - New frontmatter preview:")
                print(f"    {self._get_frontmatter_preview(new_frontmatter)}")
            else:
                # 备份原文件
                backup_path = skill_file.with_suffix('.md.bak')
                shutil.copy2(skill_file, backup_path)
                print(f"  📋 Backed up to: {backup_path.name}")

                # 写入新内容
                skill_file.write_text(new_content, encoding='utf-8')
                print(f"  ✅ Migrated successfully")

            self.results["migrated"].append(str(skill_file))
            return True

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.results["errors"].append((str(skill_file), str(e)))
            return False

    def _is_new_format(self, frontmatter: dict) -> bool:
        """检查是否已经是新格式"""
        # 新格式有明确的 execution_type 字段
        if "execution_type" in frontmatter:
            return True
        # 新格式有 triggers 结构
        if "triggers" in frontmatter and isinstance(frontmatter["triggers"], dict):
            return True
        return False

    def _generate_new_content(self, frontmatter, body_content: str) -> str:
        """生成新格式的内容"""
        import yaml
        frontmatter_dict = frontmatter.to_dict()
        yaml_str = yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True)

        return f"---\n{yaml_str}---\n\n{body_content}"

    def _get_frontmatter_preview(self, frontmatter) -> str:
        """获取frontmatter预览（前几行）"""
        lines = []
        fm_dict = frontmatter.to_dict()
        for key in ['name', 'display_name', 'execution_type', 'layer', 'priority']:
            if key in fm_dict:
                lines.append(f"    {key}: {fm_dict[key]}")
        return "\n".join(lines)

    def _print_summary(self):
        """打印迁移结果汇总"""
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)

        print(f"✅ Migrated: {len(self.results['migrated'])}")
        for item in self.results['migrated']:
            print(f"  - {Path(item).relative_to(self.skills_dir)}")

        print(f"\n⏭️  Skipped: {len(self.results['skipped'])}")
        for item in self.results['skipped']:
            print(f"  - {Path(item).relative_to(self.skills_dir)}")

        if self.results['errors']:
            print(f"\n❌ Errors: {len(self.results['errors'])}")
            for item, error in self.results['errors']:
                print(f"  - {Path(item).relative_to(self.skills_dir)}: {error}")

    def create_new_skill_template(
        self,
        name: str,
        display_name: str,
        description: str,
        keywords: List[str],
        execution_type: str = "prompt",
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        创建一个新的skill模板。

        Args:
            name: Skill名称 (kebab-case)
            display_name: 显示名称
            description: 描述
            keywords: 触发关键词
            execution_type: 执行类型
            output_dir: 输出目录 (默认为 skills/domain/)

        Returns:
            创建的skill目录路径
        """
        # 确定输出目录
        if output_dir is None:
            if execution_type == "composite":
                output_dir = self.skills_dir / "composite"
            else:
                output_dir = self.skills_dir / "domain"

        skill_dir = output_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 生成SKILL.md
        content = generate_skill_template(
            name=name,
            display_name=display_name,
            description=description,
            keywords=keywords,
            execution_type=ExecutionType(execution_type),
        )

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding='utf-8')

        # 创建子目录
        (skill_dir / "references").mkdir(exist_ok=True)
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "examples").mkdir(exist_ok=True)

        print(f"✅ Created new skill: {skill_dir.relative_to(self.skills_dir)}")

        return skill_dir

    def validate_all(self) -> List[Tuple[Path, List[str]]]:
        """
        验证所有SKILL.md文件格式。

        Returns:
            错误列表 (文件路径, 错误消息列表)
        """
        errors = []

        for skill_file in self.skills_dir.rglob("SKILL.md"):
            is_valid, validation_errors = validate_skill_frontmatter(skill_file)
            if not is_valid:
                errors.append((skill_file, validation_errors))

        return errors


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="SKILL.md格式迁移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 迁移所有SKILL.md文件
  python migrate_skill_format.py

  # 演练模式（不实际修改）
  python migrate_skill_format.py --dry-run

  # 迁移指定skill
  python migrate_skill_format.py --skill cvd-risk-assessment

  # 创建新skill模板
  python migrate_skill_format.py --create new-skill --display-name "新技能" --desc "描述" --keywords 关键词1 关键词2

  # 验证所有skills
  python migrate_skill_format.py --validate
        """
    )

    parser.add_argument(
        "--skills-dir",
        default="skills",
        help="Skills根目录 (默认: skills)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演练模式，不实际修改文件"
    )

    parser.add_argument(
        "--skill",
        help="仅迁移指定的skill名称"
    )

    parser.add_argument(
        "--create",
        help="创建新skill模板"
    )

    parser.add_argument(
        "--display-name",
        help="新skill的显示名称"
    )

    parser.add_argument(
        "--desc",
        help="新skill的描述"
    )

    parser.add_argument(
        "--keywords",
        nargs="+",
        help="新skill的触发关键词"
    )

    parser.add_argument(
        "--execution-type",
        choices=["workflow", "prompt", "composite"],
        default="prompt",
        help="新skill的执行类型"
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="验证所有SKILL.md格式"
    )

    args = parser.parse_args()

    tool = SkillMigrationTool(
        skills_dir=Path(args.skills_dir),
        dry_run=args.dry_run
    )

    if args.validate:
        print("Validating all SKILL.md files...\n")
        errors = tool.validate_all()

        if not errors:
            print("✅ All SKILL.md files are valid!")
            return

        print(f"❌ Found {len(errors)} files with errors:\n")
        for skill_file, error_list in errors:
            print(f"{skill_file.relative_to(Path(args.skills_dir))}:")
            for error in error_list:
                print(f"  - {error}")
            print()

    elif args.create:
        if not args.display_name or not args.desc or not args.keywords:
            print("❌ --create requires --display-name, --desc, and --keywords")
            return

        tool.create_new_skill_template(
            name=args.create,
            display_name=args.display_name,
            description=args.desc,
            keywords=args.keywords,
            execution_type=args.execution_type,
        )

    elif args.skill:
        skill_file = Path(args.skills_dir) / args.skill / "SKILL.md"
        if not skill_file.exists():
            # 尝试在子目录中查找
            found = list(Path(args.skills_dir).rglob(f"**/{args.skill}/SKILL.md"))
            if found:
                skill_file = found[0]
            else:
                print(f"❌ Skill not found: {args.skill}")
                return

        tool.migrate_one(skill_file)

    else:
        tool.migrate_all()


if __name__ == "__main__":
    main()
