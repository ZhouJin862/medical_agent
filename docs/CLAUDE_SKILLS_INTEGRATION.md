# Claude Agent Skills 集成方案

## 概述

本文档说明如何将 **Claude Agent Skills** 标准集成到现有的医疗智能体项目中。

---

## 核心架构对比

### 现有架构 vs Claude Skills 标准

| 维度 | 现有实现 | Claude Skills 标准 |
|------|---------|-------------------|
| 技能定义 | 数据库 `skills` 表 | 文件系统 `SKILL.md` |
| 触发机制 | API 调用 + 关键词匹配 | LLM 自主选择 (基于 description) |
| 内容加载 | 全部加载到内存 | Progressive Disclosure |
| 参数提取 | 正则表达式 + NER | LLM 提取 |
| 执行方式 | Python 函数调用 | Bash 脚本执行 |
| 可移植性 | 项目专属 | 跨平台通用 |

---

## 集成方案：混合架构

### 方案设计

```
┌─────────────────────────────────────────────────────────────┐
│                    医疗智能体系统                              │
└─────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │  Layer 1 │   │  Layer 2 │   │  Layer 3 │
       │ 基础工具  │   │ 领域技能  │   │ 组合技能  │
       └──────────┘   └──────────┘   └──────────┘
              │              │              │
              ▼              ▼              ▼
       ┌──────────────────────────────────────────────────┐
       │          Claude Skills 文件系统                   │
       │  skills/hypertension-risk-assessment/SKILL.md     │
       │  skills/hyperglycemia-risk-assessment/SKILL.md    │
       │  skills/hyperlipidemia-risk-assessment/SKILL.md   │
       │  skills/hyperuricemia-risk-assessment/SKILL.md    │
       │  skills/obesity-risk-assessment/SKILL.md          │
       │  skills/chronic-disease-risk-assessment/SKILL.md  │
       └──────────────────────────────────────────────────┘
                             │
                             ▼
       ┌──────────────────────────────────────────────────┐
       │              技能加载服务                          │
       │  - 扫描 skills/ 目录                             │
       │  - 解析 YAML frontmatter                        │
       │  - 构建 Skills Registry                          │
       └──────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │LLM 选择  │   │规则引擎   │   │脚本执行   │
       │技能      │   │评估       │   │辅助       │
       └──────────┘   └──────────┘   └──────────┘
```

---

## 实现步骤

### Step 1: 创建 Skills 文件系统

```bash
mkdir -p skills/
mkdir -p skills/hypertension-risk-assessment/{assets,scripts}
mkdir -p skills/hyperglycemia-risk-assessment/{assets,scripts}
mkdir -p skills/hyperlipidemia-risk-assessment/{assets,scripts}
mkdir -p skills/hyperuricemia-risk-assessment/{assets,scripts}
mkdir -p skills/obesity-risk-assessment/{assets,scripts}
mkdir -p skills/chronic-disease-risk-assessment/{assets,scripts}
```

### Step 2: 实现 Skills Registry 服务

```python
# src/domain/shared/services/skills_registry.py

from pathlib import Path
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str
    directory: Path
    enabled: bool = True

@dataclass
class SkillDefinition:
    """完整技能定义"""
    metadata: SkillMetadata
    content: str
    reference_files: List[str]
    scripts: List[str]


class SkillsRegistry:
    """
    Claude Skills 注册表

    扫描 skills/ 目录，解析 SKILL.md 文件，提供技能发现接口
    """

    def __init__(self, skills_dir: str = "skills"):
        self._skills_dir = Path(skills_dir)
        self._skills: Dict[str, SkillDefinition] = {}
        self._metadata_cache: Dict[str, SkillMetadata] = {}

    def scan_skills(self) -> List[SkillMetadata]:
        """
        扫描所有技能目录，提取元数据

        只读取 YAML frontmatter，不读取完整内容
        这实现了 Progressive Disclosure 的第一层
        """
        metadata_list = []

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            # 只读取 frontmatter
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                frontmatter = self._parse_frontmatter(content)

            if frontmatter:
                metadata = SkillMetadata(
                    name=frontmatter.get('name'),
                    description=frontmatter.get('description'),
                    directory=skill_dir,
                )
                metadata_list.append(metadata)
                self._metadata_cache[metadata.name] = metadata

        return metadata_list

    def get_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """获取技能元数据（不加载完整内容）"""
        return self._metadata_cache.get(skill_name)

    def load_skill(self, skill_name: str) -> Optional[SkillDefinition]:
        """
        按需加载技能完整内容

        这实现了 Progressive Disclosure 的第二层：
        只在需要时读取 SKILL.md 的完整内容
        """
        metadata = self.get_skill_metadata(skill_name)
        if not metadata:
            return None

        # 读取主文件
        skill_md = metadata.directory / "SKILL.md"
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # 发现参考文件
        reference_dir = metadata.directory / "reference"
        reference_files = []
        if reference_dir.exists():
            reference_files = [
                str(f.relative_to(metadata.directory))
                for f in reference_dir.glob("*.md")
            ]

        # 发现脚本
        scripts_dir = metadata.directory / "scripts"
        scripts = []
        if scripts_dir.exists():
            scripts = [
                str(f.relative_to(metadata.directory))
                for f in scripts_dir.glob("*.py")
            ]

        return SkillDefinition(
            metadata=metadata,
            content=content,
            reference_files=reference_files,
            scripts=scripts,
        )

    def _parse_frontmatter(self, content: str) -> Optional[dict]:
        """解析 YAML frontmatter"""
        if not content.startswith('---'):
            return None

        try:
            # 提取 frontmatter
            end = content.find('---', 3)
            if end == -1:
                return None

            frontmatter_str = content[3:end].strip()
            return yaml.safe_load(frontmatter_str)
        except Exception:
            return None
```

### Step 3: 集成到 Agent 工作流

```python
# src/infrastructure/agent/graph.py

from src.domain.shared.services.skills_registry import SkillsRegistry

class MedicalAgent:
    """集成 Claude Skills 的医疗智能体"""

    def __init__(self):
        # 初始化 Skills Registry
        self._skills_registry = SkillsRegistry()

        # 扫描所有技能（只加载元数据）
        self._available_skills = self._skills_registry.scan_skills()

    async def process(self, user_input: str, patient_id: str) -> AgentState:
        """处理用户输入"""

        # 构建系统提示，包含所有技能的描述
        skill_descriptions = self._build_skill_prompt()

        system_prompt = f"""你是医疗智能体助手。

可用技能:
{skill_descriptions}

当用户请求匹配某个技能的描述时，你应该使用该技能。
"""

        # 调用 LLM
        llm_response = await self._llm.generate(
            user_input=user_input,
            system_prompt=system_prompt,
        )

        # 检测 LLM 是否选择使用某个技能
        selected_skill = self._detect_selected_skill(llm_response)

        if selected_skill:
            # 按需加载技能内容
            skill_def = self._skills_registry.load_skill(selected_skill)

            # 使用技能内容重新生成
            enhanced_response = await self._generate_with_skill(
                skill_def=skill_def,
                user_input=user_input,
                patient_id=patient_id,
            )

            return AgentState(
                final_response=enhanced_response,
                intent=Intent.HEALTH_ASSESSMENT,
                skill_used=selected_skill,
            )
        else:
            # 直接使用 LLM 响应
            return AgentState(
                final_response=llm_response,
                intent=Intent.GENERAL,
            )

    def _build_skill_prompt(self) -> str:
        """构建技能描述提示词"""
        descriptions = []
        for skill in self._available_skills:
            descriptions.append(
                f"- **{skill.name}**: {skill.description}"
            )
        return "\n".join(descriptions)

    def _detect_selected_skill(self, response: str) -> Optional[str]:
        """
        检测 LLM 是否选择使用某个技能

        可以通过以下方式:
        1. 检测响应中的特定格式
        2. 使用 function calling
        3. 让 LLM 输出 XML 标签
        """
        # 简单实现：检测 skill_usage 标记
        import re
        match = re.search(r'<skill>(\w+)</skill>', response)
        return match.group(1) if match else None
```

### Step 4: API 集成

```python
# src/interface/api/routes/skills_v2.py

from fastapi import APIRouter, Depends
from src.domain.shared.services.skills_registry import SkillsRegistry

router = APIRouter(prefix="/api/v2/skills", tags=["skills"])

@router.get("/list")
async def list_skills(
    registry: SkillsRegistry = Depends(lambda: SkillsRegistry())
):
    """
    列出所有可用技能

    只返回元数据，不返回完整内容
    """
    skills = registry.scan_skills()
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "enabled": s.enabled,
            }
            for s in skills
        ]
    }

@router.get("/{skill_name}")
async def get_skill(
    skill_name: str,
    registry: SkillsRegistry = Depends(lambda: SkillsRegistry())
):
    """
    获取技能完整内容

    按需加载 SKILL.md 和相关文件
    """
    skill_def = registry.load_skill(skill_name)

    if not skill_def:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {
        "name": skill_def.metadata.name,
        "description": skill_def.metadata.description,
        "content": skill_def.content,
        "reference_files": skill_def.reference_files,
        "scripts": skill_def.scripts,
    }

@router.post("/{skill_name}/execute")
async def execute_skill(
    skill_name: str,
    request: SkillExecutionRequest,
    registry: SkillsRegistry = Depends(lambda: SkillsRegistry())
):
    """
    执行技能（如果有脚本）

    执行技能目录中的 Python 脚本
    """
    skill_def = registry.load_skill(skill_name)

    if not skill_def:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 执行脚本
    script_path = skill_def.metadata.directory / "scripts" / request.script_name
    result = await _execute_python_script(script_path, request.parameters)

    return {"result": result}
```

---

## 与现有系统的兼容性

### 保留数据库技能（向后兼容）

```
┌────────────────────────────────────────────────────────┐
│              混合技能存储架构                           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Claude Skills (文件系统)                              │
│  - 技能定义: SKILL.md                                  │
│  - 参考文档: reference/*.md                           │
│  - 执行脚本: scripts/*.py                              │
│                                                        │
│  Database Skills (现有)                                │
│  - 技能元数据: skills 表                               │
│  - 规则配置: rule_enhancement                         │
│  - 提示词模板: skill_prompts 表                       │
│                                                        │
│  统一访问层: SkillsRepository                          │
│  - 自动检测技能来源                                   │
│  - 统一加载接口                                       │
└────────────────────────────────────────────────────────┘
```

### 统一技能访问接口

```python
# src/domain/shared/services/unified_skills_repository.py

class UnifiedSkillsRepository:
    """
    统一技能访问接口

    同时支持:
    1. Claude Skills (文件系统)
    2. Database Skills (现有)
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._file_registry = SkillsRegistry()
        self._db_repo = SkillDatabaseRepository(session)

    async def list_skills(self) -> List[SkillInfo]:
        """列出所有技能（两种来源）"""
        skills = []

        # 从文件系统
        file_skills = self._file_registry.scan_skills()
        for skill in file_skills:
            skills.append(SkillInfo(
                id=skill.name,
                name=skill.name,
                source="file",
                description=skill.description,
            ))

        # 从数据库
        db_skills = await self._db_repo.list_all()
        for skill in db_skills:
            if not any(s.id == skill.name for s in skills):
                skills.append(SkillInfo(
                    id=skill.id,
                    name=skill.name,
                    source="database",
                    description=skill.description,
                ))

        return skills

    async def load_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """加载技能（自动检测来源）"""
        # 先尝试文件系统
        file_skill = self._file_registry.load_skill(skill_id)
        if file_skill:
            return file_skill

        # 再尝试数据库
        db_skill = await self._db_repo.get_by_name(skill_id)
        if db_skill:
            return self._convert_to_definition(db_skill)

        return None
```

---

## 迁移计划

### 阶段 1: 创建 Claude Skills 文件（1-2天）
1. 为 8 个现有技能创建 SKILL.md 文件
2. 迁移参考文档到 reference/ 目录
3. 创建辅助脚本到 scripts/ 目录

### 阶段 2: 实现 Skills Registry（1-2天）
1. 实现 SkillsRegistry 服务
2. 实现元数据扫描和缓存
3. 实现按需加载机制

### 阶段 3: 集成到 Agent（2-3天）
1. 修改 MedicalAgent 使用 SkillsRegistry
2. 实现 LLM 技能选择
3. 实现技能内容增强

### 阶段 4: 统一访问层（1-2天）
1. 实现 UnifiedSkillsRepository
2. 保持向后兼容
3. 逐步迁移数据库技能

### 阶段 5: 测试和优化（2-3天）
1. 端到端测试
2. 性能优化
3. 文档完善

---

## 优势

| 优势 | 说明 |
|------|------|
| **标准化** | 遵循 Claude 官方标准，跨平台兼容 |
| **可移植性** | 技能可独立于项目使用和分享 |
| **渐进披露** | 节省 Token，提高响应速度 |
| **易于维护** | 文件形式便于版本控制和协作 |
| **向后兼容** | 现有数据库技能继续工作 |
| **灵活扩展** | 新增技能只需添加文件 |

---

## 实施建议

1. **渐进式迁移**: 先创建 Claude Skills，保持数据库技能并行
2. **优先级**: 高血压评估技能作为试点
3. **测试验证**: 确保 LLM 能正确选择和使用技能
4. **监控观察**: 跟踪技能使用情况和效果

是否开始实施此方案？
