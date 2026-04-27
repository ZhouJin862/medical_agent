#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技能执行器工厂

根据配置选择执行后端（Subprocess 或 MS-Agent）
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from src.config.settings import get_settings
from .skill_executor_base import SkillExecutor, SkillExecutorException
from .subprocess_executor import SubprocessSkillExecutor


logger = logging.getLogger(__name__)


class SkillExecutorFactory:
    """
    技能执行器工厂

    根据配置创建合适的执行器实例：
    - subprocess: 基于 subprocess 的执行器（默认）
    - msagent: 基于 MS-Agent 库的执行器
    - auto: 自动选择（优先 msagent，回退到 subprocess）
    """

    # 默认配置
    DEFAULT_CONFIG = {
        "backend": "subprocess",  # subprocess | msagent-sandbox | auto
        "timeout": 30,
        "docker_image": "python:3.11-slim"
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None, use_settings: bool = True):
        """
        初始化工厂

        Args:
            config: 配置字典，如果为 None 则使用默认配置
            use_settings: 是否从环境变量读取配置
        """
        # 如果启用 settings 且没有提供 config，从环境变量读取
        if use_settings and config is None:
            settings = get_settings()
            config = {
                "backend": settings.skill_executor_backend,
                "timeout": settings.skill_executor_timeout,
                "docker_image": settings.skill_executor_docker_image
            }

        self.config = self._merge_config(config)

    def _merge_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """合并配置"""
        if config is None:
            return self.DEFAULT_CONFIG.copy()

        merged = self.DEFAULT_CONFIG.copy()
        merged.update(config)
        return merged

    def create_executor(self, skill_dir: Path, backend: Optional[str] = None) -> SkillExecutor:
        """
        创建执行器实例

        Args:
            skill_dir: 技能目录路径
            backend: 指定后端类型，如果为 None 则使用配置中的值

        Returns:
            SkillExecutor 实例

        Raises:
            SkillExecutorException: 如果创建失败
        """
        backend = backend or self.config["backend"]
        timeout = self.config["timeout"]

        logger.debug(f"Creating executor for {skill_dir.name} with backend: {backend}")

        if backend == "auto":
            return self._create_auto_executor(skill_dir, timeout)
        elif backend == "msagent-sandbox":
            return self._create_msagent_sandbox_executor(skill_dir, timeout)
        elif backend == "msagent":
            return self._create_msagent_executor(skill_dir, timeout)
        elif backend == "subprocess":
            return self._create_subprocess_executor(skill_dir, timeout)
        else:
            raise SkillExecutorException(f"Unknown backend: {backend}")

    def _create_subprocess_executor(self, skill_dir: Path, timeout: int) -> SkillExecutor:
        """创建 subprocess 执行器"""
        return SubprocessSkillExecutor(skill_dir, timeout=timeout)

    def _create_msagent_executor(self, skill_dir: Path, timeout: int) -> SkillExecutor:
        """创建 MS-Agent 执行器"""
        from .msagent_executor_impl import MSAgentSkillExecutor, MSAGENT_AVAILABLE

        if not MSAGENT_AVAILABLE:
            raise SkillExecutorException(
                "MS-Agent backend requested but library not installed. "
                "Install with: pip install msagent"
            )

        msagent_config = self.config["msagent"]
        return MSAgentSkillExecutor(
            skill_dir,
            timeout=timeout,
            use_sandbox=msagent_config.get("use_sandbox", False),
            llm_model=msagent_config.get("llm_model")
        )

    def _create_msagent_sandbox_executor(self, skill_dir: Path, timeout: int) -> SkillExecutor:
        """创建 MS-Agent Sandbox 执行器"""
        from .msagent_sandbox_executor import MSAgentSandboxExecutor

        try:
            docker_image = self.config.get("docker_image", "python:3.11-slim")
            return MSAgentSandboxExecutor(
                skill_dir,
                timeout=timeout,
                docker_image=docker_image
            )
        except Exception as e:
            raise SkillExecutorException(
                f"Failed to create MS-Agent Sandbox executor: {e}\n"
                "Ensure Docker is running and ms-agent is installed from: "
                "pip install git+https://github.com/modelscope/ms-agent.git"
            )

    def _create_auto_executor(self, skill_dir: Path, timeout: int) -> SkillExecutor:
        """自动选择执行器"""
        from .msagent_sandbox_executor import SANDBOX_AVAILABLE

        if SANDBOX_AVAILABLE:
            logger.debug("MS-Agent Sandbox available, using Sandbox backend")
            return self._create_msagent_sandbox_executor(skill_dir, timeout)
        else:
            logger.debug("MS-Agent Sandbox not available, using subprocess backend")
            return self._create_subprocess_executor(skill_dir, timeout)

    def get_active_backend(self) -> str:
        """获取当前激活的后端名称"""
        backend = self.config["backend"]
        if backend == "auto":
            from .msagent_sandbox_executor import SANDBOX_AVAILABLE
            return "msagent-sandbox" if SANDBOX_AVAILABLE else "subprocess"
        return backend

    def list_available_backends(self) -> Dict[str, bool]:
        """列出可用的后端"""
        from .msagent_sandbox_executor import SANDBOX_AVAILABLE

        return {
            "subprocess": True,  # 始终可用
            "msagent-sandbox": SANDBOX_AVAILABLE
        }


# 全局工厂实例（延迟初始化）
_global_factory: Optional[SkillExecutorFactory] = None


def get_executor_factory(config: Optional[Dict[str, Any]] = None) -> SkillExecutorFactory:
    """
    获取全局工厂实例

    Args:
        config: 配置字典（仅首次调用时使用）

    Returns:
        SkillExecutorFactory 实例
    """
    global _global_factory

    if _global_factory is None:
        _global_factory = SkillExecutorFactory(config)

    return _global_factory


def create_skill_executor(
    skill_dir: Path,
    backend: Optional[str] = None
) -> SkillExecutor:
    """
    创建技能执行器（便捷函数）

    Args:
        skill_dir: 技能目录路径
        backend: 指定后端类型

    Returns:
        SkillExecutor 实例
    """
    factory = get_executor_factory()
    return factory.create_executor(skill_dir, backend)


def set_executor_config(config: Dict[str, Any]):
    """
    设置执行器配置（便捷函数）

    Args:
        config: 配置字典
    """
    global _global_factory
    _global_factory = SkillExecutorFactory(config)
    logger.info(f"Executor config updated: backend={config.get('backend', 'default')}")


def get_active_backend() -> str:
    """获取当前激活的后端名称（便捷函数）"""
    factory = get_executor_factory()
    return factory.get_active_backend()


def list_available_backends() -> Dict[str, bool]:
    """列出可用的执行后端（便捷函数）"""
    factory = get_executor_factory()
    return factory.list_available_backends()
