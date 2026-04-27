"""
RecommendationAggregationService - Domain service for aggregating recommendations.

Aggregates recommendations from:
- Triage (hospital/doctor)
- Medication
- Health services
"""

import logging
from typing import List, Optional, Dict, Any

from ..value_objects.triage_recommendation import TriageRecommendation
from ..value_objects.medication_recommendation import MedicationRecommendationResult
from ..value_objects.service_recommendation import ServiceRecommendation

logger = logging.getLogger(__name__)


@dataclass
class AggregatedRecommendations:
    """
    Aggregated recommendations from all sources.

    Attributes:
        triage: Triage recommendations
        medication: Medication recommendations
        services: Health service recommendations
        summary: Summary of all recommendations
        priority_actions: Priority action items
    """

    triage: Optional[TriageRecommendation] = None
    medication: Optional[MedicationRecommendationResult] = None
    services: Optional[ServiceRecommendation] = None
    summary: str = ""
    priority_actions: List[str] = None

    def __post_init__(self):
        if self.priority_actions is None:
            self.priority_actions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "triage": self.triage.to_dict() if self.triage else None,
            "medication": self.medication.to_dict() if self.medication else None,
            "services": self.services.to_dict() if self.services else None,
            "summary": self.summary,
            "priority_actions": self.priority_actions,
        }


class RecommendationAggregationService:
    """
    Domain service for aggregating health recommendations.

    Collects and prioritizes recommendations from multiple sources
    to provide a comprehensive set of next steps for the patient.
    """

    def __init__(self):
        """Initialize the service."""
        logger.info("RecommendationAggregationService initialized")

    async def aggregate(
        self,
        triage: Optional[TriageRecommendation] = None,
        medication: Optional[MedicationRecommendationResult] = None,
        services: Optional[ServiceRecommendation] = None,
    ) -> AggregatedRecommendations:
        """
        Aggregate recommendations from all sources.

        Args:
            triage: Triage recommendations
            medication: Medication recommendations
            services: Health service recommendations

        Returns:
            Aggregated recommendations with priority actions
        """
        # Determine priority actions based on triage urgency
        priority_actions = []

        if triage:
            if triage.priority.value == "urgent":
                priority_actions.append(
                    f"⚠️ 紧急：建议立即就医。{triage.reason}"
                )
            elif triage.priority.value == "soon":
                priority_actions.append(
                    f"🏥 尽快：建议近期就诊。{triage.reason}"
                )

            # Add hospital/doctor recommendations
            if triage.get_primary_hospital():
                hospital = triage.get_primary_hospital()
                priority_actions.append(
                    f"推荐医院：{hospital.name}（{hospital.distance_km}km）"
                )

            if triage.get_primary_department():
                dept = triage.get_primary_department()
                priority_actions.append(f"挂号科室：{dept.name}")

        # Add medication warnings
        if medication and medication.has_contraindications():
            priority_actions.append("⚠️ 用药警告：当前用药存在禁忌，请咨询医生")

        # Add service recommendations
        if services:
            top_insurance = services.get_top_insurance(1)
            if top_insurance:
                for product in top_insurance:
                    if product.strength.value == "highly_recommended":
                        priority_actions.append(
                            f"推荐保险：{product.name}"
                        )

        # Generate summary
        summary = self._generate_summary(triage, medication, services)

        return AggregatedRecommendations(
            triage=triage,
            medication=medication,
            services=services,
            summary=summary,
            priority_actions=priority_actions,
        )

    def _generate_summary(
        self,
        triage: Optional[TriageRecommendation],
        medication: Optional[MedicationRecommendationResult],
        services: Optional[ServiceRecommendation],
    ) -> str:
        """Generate a summary of all recommendations."""
        parts = ["## 健康建议汇总\n"]

        if triage:
            parts.append(f"### 就医建议\n{triage.reason}\n")

            if triage.hospitals:
                parts.append("**推荐医院：**")
                for hospital in triage.hospitals[:3]:
                    parts.append(
                        f"- {hospital.name}（{hospital.distance_km}km，{hospital.rating}星）"
                    )

        if medication:
            parts.append("\n### 用药建议")

            if medication.current_medications:
                parts.append("**当前用药评估：**")
                for med in medication.current_medications:
                    parts.append(f"- {med.name}: {med.status.value}")

            if medication.interactions:
                parts.append("**用药注意：**")
                for interaction in medication.interactions:
                    parts.append(f"- {interaction}")

        if services:
            parts.append("\n### 服务推荐")

            if services.insurance_products:
                parts.append("**推荐保险产品：**")
                for product in services.insurance_products[:3]:
                    parts.append(f"- {product.name}: {product.reason}")

            if services.health_services:
                parts.append("**推荐服务：**")
                for service in services.health_services[:3]:
                    parts.append(f"- {service.name}: {service.description}")

        return "\n".join(parts)

    def filter_by_priority(
        self,
        recommendations: AggregatedRecommendations,
        min_priority: str = "routine",
    ) -> AggregatedRecommendations:
        """
        Filter recommendations by priority level.

        Args:
            recommendations: Full recommendations
            min_priority: Minimum priority to include

        Returns:
            Filtered recommendations
        """
        # Priority levels: urgent > soon > routine > optional
        priority_order = {"urgent": 4, "soon": 3, "routine": 2, "optional": 1}
        min_level = priority_order.get(min_priority, 0)

        filtered = AggregatedRecommendations(
            triage=None,
            medication=recommendations.medication,
            services=recommendations.services,
            summary=recommendations.summary,
            priority_actions=[],
        )

        # Filter triage by priority
        if recommendations.triage:
            current_level = priority_order.get(
                recommendations.triage.priority.value, 0
            )
            if current_level >= min_level:
                filtered.triage = recommendations.triage

        # Keep priority actions that match the level
        for action in recommendations.priority_actions:
            # Simple heuristic: urgent actions contain ⚠️, soon actions contain 🏥
            if min_priority == "urgent" and "⚠️" in action:
                filtered.priority_actions.append(action)
            elif min_priority == "soon" and ("⚠️" in action or "🏥" in action):
                filtered.priority_actions.append(action)
            elif min_priority == "routine":
                filtered.priority_actions.append(action)

        return filtered
