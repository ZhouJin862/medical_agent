"""
Database session management.

Provides async engine and session management for SQLAlchemy.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global engine and session maker
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async database engine."""
    global _engine

    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        logger.info(f"Database engine created: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker."""
    global _session_maker

    if _session_maker is None:
        engine = get_engine()
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.

    Usage in FastAPI:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_db_session)):
            ...

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session.

    Usage:
        async with get_db_session_context() as session:
            # Use session here
            ...

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """Initialize database - create tables if needed."""
    # Import all models to register them with SQLAlchemy metadata
    from src.infrastructure.persistence.models import (
        Base,
        RuleModel,
        RuleExecutionHistoryModel,
        VitalSignStandardModel,
        RiskScoreRuleModel,
        SkillModel,
        SkillPromptModel,
        SkillModelConfigModel,
        ConsultationModel,
        MessageModel,
        GuidelineModel,
    )

    engine = get_engine()

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")

        # Initialize default data
        await _init_default_standards(conn)
        await _init_default_rules(conn)


async def _init_default_standards(conn) -> None:
    """Initialize default vital sign standards if empty."""
    from src.infrastructure.persistence.models.rule_models import VitalSignStandardModel
    from sqlalchemy import select

    # Check if standards already exist
    result = await conn.execute(select(VitalSignStandardModel).limit(1))
    if result.scalar():
        logger.info("Vital sign standards already initialized")
        return

    # Insert default standards
    standards = [
        # Blood pressure standards (mmHg)
        {
            "name": "bp_systolic_normal",
            "display_name": "收缩压正常值",
            "description": "正常收缩压范围",
            "vital_sign_type": "blood_pressure",
            "normal_min": 90,
            "normal_max": 140,
            "high_risk_min": 160,
            "very_high_risk_min": 180,
            "unit": "mmHg",
            "enabled": True,
        },
        {
            "name": "bp_diastolic_normal",
            "display_name": "舒张压正常值",
            "description": "正常舒张压范围",
            "vital_sign_type": "blood_pressure",
            "normal_min": 60,
            "normal_max": 90,
            "high_risk_min": 100,
            "very_high_risk_min": 110,
            "unit": "mmHg",
            "enabled": True,
        },
        # Blood glucose standards (mmol/L)
        {
            "name": "fasting_glucose_normal",
            "display_name": "空腹血糖正常值",
            "description": "空腹血糖正常范围",
            "vital_sign_type": "blood_glucose",
            "normal_min": 3.9,
            "normal_max": 6.1,
            "high_risk_min": 7.0,
            "very_high_risk_min": 11.1,
            "unit": "mmol/L",
            "enabled": True,
        },
        {
            "name": "postprandial_glucose_normal",
            "display_name": "餐后2小时血糖正常值",
            "description": "餐后2小时血糖正常范围",
            "vital_sign_type": "blood_glucose",
            "normal_min": 4.4,
            "normal_max": 7.8,
            "high_risk_min": 11.1,
            "very_high_risk_min": 15.0,
            "unit": "mmol/L",
            "enabled": True,
        },
        # BMI standards
        {
            "name": "bmi_normal",
            "display_name": "BMI正常值",
            "description": "体重指数正常范围",
            "vital_sign_type": "bmi",
            "normal_min": 18.5,
            "normal_max": 23.9,
            "high_risk_min": 24.0,
            "very_high_risk_min": 28.0,
            "unit": "kg/m²",
            "enabled": True,
        },
        # Total cholesterol standards (mmol/L)
        {
            "name": "total_cholesterol_normal",
            "display_name": "总胆固醇正常值",
            "description": "总胆固醇正常范围",
            "vital_sign_type": "lipid_profile",
            "normal_min": 3.1,
            "normal_max": 5.2,
            "high_risk_min": 6.2,
            "very_high_risk_min": 7.8,
            "unit": "mmol/L",
            "enabled": True,
        },
        # Uric acid standards (μmol/L)
        {
            "name": "uric_acid_normal",
            "display_name": "血尿酸正常值",
            "description": "血尿酸正常范围",
            "vital_sign_type": "uric_acid",
            "normal_min": 150,
            "normal_max": 420,
            "high_risk_min": 480,
            "very_high_risk_min": 600,
            "unit": "μmol/L",
            "enabled": True,
        },
    ]

    for std_data in standards:
        try:
            await conn.execute(VitalSignStandardModel.__table__.insert().values(**std_data))
            logger.info(f"Created standard: {std_data['name']}")
        except Exception as e:
            logger.warning(f"Failed to create standard {std_data['name']}: {e}")

    logger.info(f"Initialized {len(standards)} default vital sign standards")


async def _init_default_rules(conn) -> None:
    """Initialize default rules if table is empty."""
    from src.infrastructure.persistence.models.rule_models import RuleModel
    from sqlalchemy import select

    # Check if rules already exist
    result = await conn.execute(select(RuleModel).limit(1))
    if result.scalar():
        logger.info("Rules already initialized")
        return

    from src.infrastructure.persistence.models.default_rules import get_default_rules

    rules_data = get_default_rules()

    for rule_data in rules_data:
        try:
            await conn.execute(RuleModel.__table__.insert().values(**rule_data))
            logger.info(f"Created rule: {rule_data['name']}")
        except Exception as e:
            logger.warning(f"Failed to create rule {rule_data['name']}: {e}")

    logger.info(f"Initialized {len(rules_data)} default rules")


async def close_database() -> None:
    """Close database connections."""
    global _engine, _session_maker

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("Database connections closed")
