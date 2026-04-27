"""
ServiceRecommendation Value Object - Health service recommendations.

Encapsulates recommendations for:
- Insurance products
- Health management services
- Wellness programs
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ServiceCategory(Enum):
    """Categories of health services."""

    INSURANCE = "insurance"  # 保险产品
    HEALTH_MANAGEMENT = "health_management"  # 健康管理
    WELLNESS = "wellness"  # 康养服务
    CHECKUP = "checkup"  # 体检服务
    REHABILITATION = "rehabilitation"  # 康复服务


class RecommendationStrength(Enum):
    """Strength of recommendation."""

    HIGHLY_RECOMMENDED = "highly_recommended"  # 强烈推荐
    RECOMMENDED = "recommended"  # 推荐
    CONSIDER = "consider"  # 可以考虑
    OPTIONAL = "optional"  # 可选


@dataclass
class InsuranceProduct:
    """
    Insurance product recommendation.

    Attributes:
        product_id: Product identifier
        name: Product name
        provider: Insurance provider
        coverage: Coverage description
        premium: Premium amount
        strength: Recommendation strength
        reason: Reason for recommendation
    """

    product_id: str
    name: str
    provider: str
    coverage: str
    premium: str
    strength: RecommendationStrength
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "provider": self.provider,
            "coverage": self.coverage,
            "premium": self.premium,
            "strength": self.strength.value,
            "reason": self.reason,
        }


@dataclass
class HealthService:
    """
    Health service recommendation.

    Attributes:
        service_id: Service identifier
        name: Service name
        category: Service category
        description: Service description
        provider: Service provider
        price: Price information
        strength: Recommendation strength
        reason: Reason for recommendation
    """

    service_id: str
    name: str
    category: ServiceCategory
    description: str
    provider: str
    price: str
    strength: RecommendationStrength
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_id": self.service_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "provider": self.provider,
            "price": self.price,
            "strength": self.strength.value,
            "reason": self.reason,
        }


@dataclass
class ServiceRecommendation:
    """
    Complete service recommendation result.

    Attributes:
        insurance_products: Recommended insurance products
        health_services: Recommended health services
        priority_order: Order of priority for recommendations
    """

    insurance_products: List[InsuranceProduct] = field(default_factory=list)
    health_services: List[HealthService] = field(default_factory=list)
    priority_order: List[str] = field(default_factory=list)

    def get_top_insurance(self, n: int = 3) -> List[InsuranceProduct]:
        """Get top n insurance recommendations."""
        return self.insurance_products[:n]

    def get_top_services(self, n: int = 3) -> List[HealthService]:
        """Get top n service recommendations."""
        return self.health_services[:n]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insurance_products": [p.to_dict() for p in self.insurance_products],
            "health_services": [s.to_dict() for s in self.health_services],
            "priority_order": self.priority_order,
        }
