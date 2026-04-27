"""
Knowledge Base Query Service

Provides intelligent search and retrieval of medical guidelines
and knowledge base content for health assessment skills.
"""

import logging
from typing import Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session_context
from src.infrastructure.persistence.models.guideline_models import GuidelineModel
from src.infrastructure.persistence.models.skill_models import KnowledgeBaseModel

logger = logging.getLogger(__name__)


class SearchQueryType(Enum):
    """Types of search queries."""
    DISEASE = "disease"           # Search by disease code
    SYMPTOM = "symptom"           # Search by symptoms
    TREATMENT = "treatment"       # Search by treatment options
    CATEGORY = "category"         # Search by guideline category
    FULLTEXT = "fulltext"         # Full-text search


@dataclass
class SearchResult:
    """
    Knowledge base search result.

    Attributes:
        source_type: Type of source (guideline, knowledge_base)
        source_id: ID of the source record
        title: Title of the content
        category: Content category
        relevance_score: Relevance score (0-1)
        content_preview: Preview of the content
        full_content: Full content (optional, lazy loaded)
        metadata: Additional metadata
    """
    source_type: str
    source_id: str
    title: str
    category: str
    relevance_score: float
    content_preview: str
    full_content: Optional[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class KnowledgeBaseQueryService:
    """
    Service for querying medical guidelines and knowledge base.

    Provides:
    - Search by disease type
    - Search by symptoms
    - Search by treatment options
    - Full-text search
    - Category-based filtering
    """

    @classmethod
    async def search_by_disease(
        cls,
        disease_code: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search guidelines and knowledge by disease code.

        Args:
            disease_code: Disease code (e.g., "HYPERTENSION", "DIABETES")
            category: Optional category filter (prevention, treatment, etc.)
            limit: Maximum results to return

        Returns:
            List of search results
        """
        results = []

        # Search guidelines
        async with get_db_session_context() as session:
            # Query guidelines
            query = select(GuidelineModel).where(
                GuidelineModel.disease_code == disease_code,
                GuidelineModel.enabled == True,
            )

            if category:
                query = query.where(GuidelineModel.category == category)

            query = query.limit(limit)
            guideline_result = await session.execute(query)
            guidelines = guideline_result.scalars().all()

            for guideline in guidelines:
                # Get category-specific content
                content = cls._extract_category_content(guideline, category)
                preview = content[:200] if content else ""

                results.append(SearchResult(
                    source_type="guideline",
                    source_id=guideline.name,
                    title=guideline.display_name,
                    category=guideline.category,
                    relevance_score=1.0,
                    content_preview=preview,
                    metadata={
                        "version": guideline.version,
                        "publisher": guideline.publisher,
                        "year": guideline.publication_year,
                        "evidence_level": guideline.evidence_level,
                    }
                ))

            # Query knowledge base
            kb_query = select(KnowledgeBaseModel).where(
                KnowledgeBaseModel.disease_code == disease_code,
            )

            if category:
                # Map category to knowledge type
                kb_query = kb_query.where(
                    KnowledgeBaseModel.knowledge_type == category
                )

            kb_query = kb_query.limit(limit)
            kb_result = await session.execute(kb_query)
            kb_entries = kb_result.scalars().all()

            for kb in kb_entries:
                results.append(SearchResult(
                    source_type="knowledge_base",
                    source_id=kb.code,
                    title=kb.title,
                    category=kb.knowledge_type.value,
                    relevance_score=1.0,
                    content_preview=kb.content[:200],
                    metadata={
                        "version": kb.version,
                        "source": kb.source,
                        "tags": kb.tags or [],
                    }
                ))

        return results

    @classmethod
    async def search_by_symptoms(
        cls,
        symptoms: List[str],
        disease_code: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search knowledge by symptoms.

        Args:
            symptoms: List of symptom keywords
            disease_code: Optional disease filter
            limit: Maximum results

        Returns:
            List of search results
        """
        results = []

        async with get_db_session_context() as session:
            # Search in knowledge base content
            conditions = []
            for symptom in symptoms:
                conditions.append(
                    KnowledgeBaseModel.content.contains(symptom)
                )

            query = select(KnowledgeBaseModel).where(
                or_(*conditions)
            )

            if disease_code:
                query = query.where(KnowledgeBaseModel.disease_code == disease_code)

            query = query.limit(limit)
            kb_result = await session.execute(query)
            kb_entries = kb_result.scalars().all()

            for kb in kb_entries:
                # Calculate relevance based on symptom matches
                content_lower = kb.content.lower()
                matches = sum(1 for s in symptoms if s.lower() in content_lower)
                relevance = min(matches / len(symptoms), 1.0)

                results.append(SearchResult(
                    source_type="knowledge_base",
                    source_id=kb.code,
                    title=kb.title,
                    category=kb.knowledge_type.value,
                    relevance_score=relevance,
                    content_preview=kb.content[:200],
                    metadata={
                        "version": kb.version,
                        "source": kb.source,
                        "matched_symptoms": matches,
                    }
                ))

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results

    @classmethod
    async def search_by_treatment(
        cls,
        treatment_keywords: List[str],
        disease_code: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search treatment guidelines.

        Args:
            treatment_keywords: Treatment-related keywords
            disease_code: Optional disease filter
            limit: Maximum results

        Returns:
            List of search results
        """
        results = []

        async with get_db_session_context() as session:
            # Search guidelines with treatment category
            query = select(GuidelineModel).where(
                GuidelineModel.enabled == True,
            )

            if disease_code:
                query = query.where(GuidelineModel.disease_code == disease_code)

            query = query.where(
                or_(
                    GuidelineModel.category == "treatment",
                    GuidelineModel.category == "comprehensive",
                )
            )

            query = query.limit(limit)
            guideline_result = await session.execute(query)
            guidelines = guideline_result.scalars().all()

            for guideline in guidelines:
                # Get treatment content
                treatment_content = guideline.get_treatment_guidelines()
                content_str = str(treatment_content)

                # Check keyword matches
                matches = sum(1 for kw in treatment_keywords
                            if kw.lower() in content_str.lower())
                relevance = min(matches / len(treatment_keywords), 1.0) if treatment_keywords else 0.5

                results.append(SearchResult(
                    source_type="guideline",
                    source_id=guideline.name,
                    title=f"{guideline.display_name} - 治疗指南",
                    category="treatment",
                    relevance_score=relevance,
                    content_preview=str(treatment_content)[:300],
                    metadata={
                        "version": guideline.version,
                        "publisher": guideline.publisher,
                        "pharmacological": "pharmacological" in treatment_content,
                        "non_pharmacological": "non_pharmacological" in treatment_content,
                    }
                ))

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results

    @classmethod
    async def search_by_category(
        cls,
        category: str,
        disease_code: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search by guideline category.

        Args:
            category: Category (prevention, treatment, diagnosis, monitoring, lifestyle)
            disease_code: Optional disease filter
            limit: Maximum results

        Returns:
            List of search results
        """
        results = []

        async with get_db_session_context() as session:
            # Search guidelines
            guideline_query = select(GuidelineModel).where(
                GuidelineModel.category == category,
                GuidelineModel.enabled == True,
            )

            if disease_code:
                guideline_query = guideline_query.where(
                    GuidelineModel.disease_code == disease_code
                )

            guideline_query = guideline_query.limit(limit)
            g_result = await session.execute(guideline_query)
            guidelines = g_result.scalars().all()

            for guideline in guidelines:
                content = cls._extract_category_content(guideline, category)
                preview = content[:200] if content else ""

                results.append(SearchResult(
                    source_type="guideline",
                    source_id=guideline.name,
                    title=guideline.display_name,
                    category=category,
                    relevance_score=1.0,
                    content_preview=preview,
                    metadata={
                        "version": guideline.version,
                        "publisher": guideline.publisher,
                    }
                ))

            # Search knowledge base
            kb_query = select(KnowledgeBaseModel).where(
                KnowledgeBaseModel.knowledge_type == category,
            )

            if disease_code:
                kb_query = kb_query.where(
                    KnowledgeBaseModel.disease_code == disease_code
                )

            kb_query = kb_query.limit(limit)
            kb_result = await session.execute(kb_query)
            kb_entries = kb_result.scalars().all()

            for kb in kb_entries:
                results.append(SearchResult(
                    source_type="knowledge_base",
                    source_id=kb.code,
                    title=kb.title,
                    category=kb.knowledge_type.value,
                    relevance_score=1.0,
                    content_preview=kb.content[:200],
                    metadata={
                        "source": kb.source,
                        "tags": kb.tags or [],
                    }
                ))

        return results

    @classmethod
    async def fulltext_search(
        cls,
        query: str,
        disease_code: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Full-text search across guidelines and knowledge base.

        Args:
            query: Search query string
            disease_code: Optional disease filter
            limit: Maximum results

        Returns:
            List of search results
        """
        results = []
        query_lower = query.lower()

        async with get_db_session_context() as session:
            # Search guidelines
            g_query = select(GuidelineModel).where(
                GuidelineModel.enabled == True,
            )

            if disease_code:
                g_query = g_query.where(GuidelineModel.disease_code == disease_code)

            g_query = g_query.limit(limit)
            g_result = await session.execute(g_query)
            guidelines = g_result.scalars().all()

            for guideline in guidelines:
                # Search in title, description, and content
                searchable_text = f"{guideline.display_name} {guideline.description or ''} {str(guideline.guideline_content)}".lower()

                if query_lower in searchable_text:
                    # Calculate simple relevance based on position and frequency
                    position = searchable_text.find(query_lower)
                    relevance = 1.0 / (1 + position / 1000)  # Earlier matches score higher

                    results.append(SearchResult(
                        source_type="guideline",
                        source_id=guideline.name,
                        title=guideline.display_name,
                        category=guideline.category,
                        relevance_score=relevance,
                        content_preview=guideline.description[:200] if guideline.description else "",
                        metadata={
                            "version": guideline.version,
                            "publisher": guideline.publisher,
                        }
                    ))

            # Search knowledge base
            kb_query = select(KnowledgeBaseModel)

            if disease_code:
                kb_query = kb_query.where(KnowledgeBaseModel.disease_code == disease_code)

            kb_query = kb_query.limit(limit)
            kb_result = await session.execute(kb_query)
            kb_entries = kb_result.scalars().all()

            for kb in kb_entries:
                searchable_text = f"{kb.title} {kb.content}".lower()

                if query_lower in searchable_text:
                    position = searchable_text.find(query_lower)
                    relevance = 1.0 / (1 + position / 500)

                    results.append(SearchResult(
                        source_type="knowledge_base",
                        source_id=kb.code,
                        title=kb.title,
                        category=kb.knowledge_type.value,
                        relevance_score=relevance,
                        content_preview=kb.content[:200],
                        metadata={
                            "source": kb.source,
                            "tags": kb.tags or [],
                        }
                    ))

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:limit]

    @classmethod
    def _extract_category_content(
        cls,
        guideline: GuidelineModel,
        category: Optional[str],
    ) -> str:
        """
        Extract category-specific content from guideline.

        Args:
            guideline: Guideline model
            category: Category to extract (or all if None)

        Returns:
            Extracted content as string
        """
        if category:
            content_map = {
                "prevention": guideline.get_prevention_recommendations(),
                "treatment": guideline.get_treatment_guidelines(),
                "lifestyle": guideline.get_lifestyle_recommendations(),
                "monitoring": guideline.get_monitoring_requirements(),
            }
            return str(content_map.get(category, {}))
        else:
            return str(guideline.guideline_content)

    @classmethod
    async def get_risk_thresholds(
        cls,
        disease_code: str,
    ) -> Optional[dict]:
        """
        Get risk thresholds for a disease.

        Args:
            disease_code: Disease code

        Returns:
            Risk thresholds dict or None
        """
        async with get_db_session_context() as session:
            result = await session.execute(
                select(GuidelineModel).where(
                    GuidelineModel.disease_code == disease_code,
                    GuidelineModel.enabled == True,
                )
            )
            guideline = result.scalar_one_or_none()

        if guideline:
            return guideline.get_risk_thresholds()

        return None

    @classmethod
    async def get_prevention_recommendations(
        cls,
        disease_code: str,
    ) -> List[dict]:
        """
        Get prevention recommendations for a disease.

        Args:
            disease_code: Disease code

        Returns:
            List of prevention recommendations
        """
        async with get_db_session_context() as session:
            result = await session.execute(
                select(GuidelineModel).where(
                    GuidelineModel.disease_code == disease_code,
                    GuidelineModel.enabled == True,
                )
            )
            guideline = result.scalar_one_or_none()

        if guideline:
            recs = guideline.get_prevention_recommendations()
            if isinstance(recs, dict):
                # Flatten the dict to list
                return [
                    {"type": k, "recommendations": v}
                    for k, v in recs.items()
                    if v
                ]
            return recs if isinstance(recs, list) else []

        return []

    @classmethod
    async def get_lifestyle_recommendations(
        cls,
        disease_code: str,
    ) -> dict:
        """
        Get lifestyle recommendations for a disease.

        Args:
            disease_code: Disease code

        Returns:
            Lifestyle recommendations dict
        """
        async with get_db_session_context() as session:
            result = await session.execute(
                select(GuidelineModel).where(
                    GuidelineModel.disease_code == disease_code,
                    GuidelineModel.enabled == True,
                )
            )
            guideline = result.scalar_one_or_none()

        if guideline:
            return guideline.get_lifestyle_recommendations()

        return {}
