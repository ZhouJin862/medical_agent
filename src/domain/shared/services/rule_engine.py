"""
Rule Engine - Executes configured business rules.

Provides dynamic evaluation of health assessment, risk prediction,
and health plan generation rules without hardcoded logic.
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models.rule_models import (
    RuleModel,
    RuleType,
    RuleCategory,
    RuleTargetType,
    RuleExecutionHistoryModel,
    VitalSignStandardModel,
    RiskScoreRuleModel,
)
from src.infrastructure.persistence.models.base import Base

logger = logging.getLogger(__name__)


@dataclass
class RuleExecutionContext:
    """Context for rule execution."""
    patient_id: str
    input_data: Dict[str, Any]
    consultation_id: Optional[str] = None
    skill_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation."""
    rule_id: str
    rule_name: str
    matched: bool
    result: Dict[str, Any]
    confidence: float
    execution_time_ms: int
    error: Optional[str] = None


class RuleEngine:
    """
    Executes configured business rules.

    Supports:
    - Threshold rules (e.g., BP > 140/90)
    - Range rules (e.g., BMI 18.5-24.9)
    - Score rules (e.g., risk score calculation)
    - Conditional rules (complex logic)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the rule engine.

        Args:
            session: Database session for loading rules
        """
        self._session = session
        self._rule_cache: Optional[Dict[str, RuleModel]] = None

    async def evaluate_rules(
        self,
        context: RuleExecutionContext,
        categories: Optional[List[str]] = None,
        disease_code: Optional[str] = None,
    ) -> List[RuleEvaluationResult]:
        """
        Evaluate rules for the given context.

        Args:
            context: Execution context with input data
            categories: Filter by rule categories
            disease_code: Filter by disease code

        Returns:
            List of evaluation results
        """
        # Load applicable rules
        rules = await self._load_rules(categories, disease_code)

        results = []
        for rule in rules:
            if not rule.is_enabled:
                continue

            start_time = datetime.now()
            try:
                result = await self._evaluate_rule(rule, context)
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

                results.append(RuleEvaluationResult(
                    rule_id=rule.id,
                    rule_name=rule.display_name,
                    matched=result["matched"],
                    result=result,
                    confidence=result.get("confidence", 1.0),
                    execution_time_ms=execution_time,
                ))

                # Log execution
                await self._log_execution(rule, context, result, execution_time, None)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_name}: {e}")
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

                results.append(RuleEvaluationResult(
                    rule_id=rule.id,
                    rule_name=rule.display_name,
                    matched=False,
                    result={"error": str(e)},
                    confidence=0.0,
                    execution_time_ms=execution_time,
                    error=str(e),
                ))

                await self._log_execution(rule, context, {"matched": False, "error": str(e)}, execution_time, str(e))

        # Sort by priority and match status
        results.sort(key=lambda r: (not r.matched, -r.confidence))

        return results

    async def evaluate_vital_signs(
        self,
        patient_id: str,
        vital_signs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate vital signs against reference standards.

        Args:
            patient_id: Patient identifier
            vital_signs: Dictionary of vital sign values
                {
                    "systolic": 120, "diastolic": 80,
                    "fasting_glucose": 5.5,
                    "bmi": 23.5, ...
                }

        Returns:
            Dictionary with risk levels for each vital sign
        """
        results = {}

        for sign_name, sign_value in vital_signs.items():
            if sign_value is None:
                continue

            # Get standard for this vital sign
            standard = await self._get_vital_sign_standard(sign_name)
            if not standard or not standard.is_enabled:
                continue

            # Evaluate risk level
            risk_level = standard.get_risk_level(
                float(sign_value),
                gender=vital_signs.get("gender", "male"),
                age=vital_signs.get("age"),
            )

            results[sign_name] = {
                "value": sign_value,
                "risk_level": risk_level,
                "standard_id": standard.id,
                "unit": standard.unit,
            }

        return results

    async def calculate_risk_score(
        self,
        patient_id: str,
        disease_code: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate risk score for a specific disease.

        Args:
            patient_id: Patient identifier
            disease_code: Disease code (e.g., 'hypertension', 'diabetes')
            input_data: Input factors for risk calculation

        Returns:
            Risk score and level
        """
        # Get scoring rule for this disease
        rule = await self._get_risk_score_rule(disease_code)
        if not rule or not rule.is_enabled:
            return {
                "error": f"No scoring rule found for disease: {disease_code}"
            }

        return rule.calculate_score(input_data)

    async def _load_rules(
        self,
        categories: Optional[List[str]] = None,
        disease_code: Optional[str] = None,
    ) -> List[RuleModel]:
        """Load rules from database."""
        stmt = select(RuleModel).where(RuleModel.is_enabled == True)

        conditions = []
        if categories:
            conditions.append(RuleModel.rule_category.in_(categories))
        if disease_code:
            conditions.append(RuleModel.disease_code == disease_code)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(RuleModel.rule_priority.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _evaluate_rule(
        self,
        rule: RuleModel,
        context: RuleExecutionContext,
    ) -> Dict[str, Any]:
        """Evaluate a single rule."""
        rule_type = rule.rule_type
        config = rule.rule_config

        if rule_type == RuleType.THRESHOLD:
            return self._evaluate_threshold_rule(config, context.input_data)
        elif rule_type == RuleType.RANGE:
            return self._evaluate_range_rule(config, context.input_data)
        elif rule_type == RuleType.SCORE:
            return self._evaluate_score_rule(config, context.input_data)
        elif rule_type == RuleType.CONDITION:
            return self._evaluate_condition_rule(config, context.input_data)
        else:
            return {"matched": False, "error": f"Unknown rule type: {rule_type}"}

    def _evaluate_threshold_rule(self, config: Dict, input_data: Dict) -> Dict[str, Any]:
        """Evaluate threshold rule - supports both single field and multiple conditions formats."""
        logic = config.get("logic", "AND").upper()
        confidence = config.get("confidence", 1.0)

        # Check if this is a multi-condition format (like hypertension rules)
        conditions = config.get("conditions")

        if conditions:
            # Multi-condition format: [{"field": "systolic", "operator": ">=", "threshold": 140}, ...]
            results = []
            for condition in conditions:
                field = condition.get("field")
                operator = condition.get("operator", ">=")
                threshold = condition.get("threshold")
                value = input_data.get(field)

                if value is None:
                    matched = False
                else:
                    matched = self._compare_values(value, operator, threshold)

                results.append(matched)

            # Apply logic (AND/OR)
            if logic == "OR":
                matched = any(results)
            else:  # AND
                matched = all(results)

            return {
                "matched": matched,
                "confidence": confidence if matched else confidence * 0.5,
                "reason": f"Conditions ({logic}): {results}",
            }
        else:
            # Single field format
            field = config.get("field")
            operator = config.get("operator", ">=")
            threshold = config.get("threshold")
            value = input_data.get(field)

            if value is None:
                return {"matched": False, "reason": f"Field {field} not provided"}

            matched = self._compare_values(value, operator, threshold)

            return {
                "matched": matched,
                "confidence": confidence,
                "reason": f"{field} {operator} {threshold}: {value}",
            }

    def _evaluate_range_rule(self, config: Dict, input_data: Dict) -> Dict[str, Any]:
        """Evaluate range rule - supports both single field and blood pressure dual-field formats."""
        logic = config.get("logic", "AND").upper()
        confidence = config.get("confidence", 1.0)

        # Check if this is blood pressure format (systolic_min/max, diastolic_min/max)
        if "systolic_min" in config or "systolic_max" in config:
            return self._evaluate_bp_range_rule(config, input_data)

        # Standard single-field range format
        field = config.get("field")
        min_val = config.get("min")
        max_val = config.get("max")
        value = input_data.get(field)

        if value is None:
            return {"matched": False, "reason": f"Field {field} not provided"}

        matched = True
        if min_val is not None and value < min_val:
            matched = False
        if max_val is not None and value > max_val:
            matched = False

        return {
            "matched": matched,
            "confidence": confidence,
            "reason": f"{field} in range [{min_val}, {max_val}]: {value}",
        }

    def _evaluate_bp_range_rule(self, config: Dict, input_data: Dict) -> Dict[str, Any]:
        """Evaluate blood pressure range rule with systolic and diastolic ranges."""
        logic = config.get("logic", "OR").upper()
        confidence = config.get("confidence", 1.0)

        systolic = input_data.get("systolic")
        diastolic = input_data.get("diastolic")

        if systolic is None or diastolic is None:
            return {"matched": False, "reason": "Both systolic and diastolic values required"}

        # Check systolic range
        sys_min = config.get("systolic_min")
        sys_max = config.get("systolic_max")
        systolic_in_range = True
        if sys_min is not None and systolic < sys_min:
            systolic_in_range = False
        if sys_max is not None and systolic > sys_max:
            systolic_in_range = False

        # Check diastolic range
        dia_min = config.get("diastolic_min")
        dia_max = config.get("diastolic_max")
        diastolic_in_range = True
        if dia_min is not None and diastolic < dia_min:
            diastolic_in_range = False
        if dia_max is not None and diastolic > dia_max:
            diastolic_in_range = False

        # Apply logic
        if logic == "OR":
            matched = systolic_in_range or diastolic_in_range
        else:  # AND
            matched = systolic_in_range and diastolic_in_range

        return {
            "matched": matched,
            "confidence": confidence,
            "systolic": systolic,
            "diastolic": diastolic,
            "systolic_in_range": systolic_in_range,
            "diastolic_in_range": diastolic_in_range,
            "reason": f"BP {systolic}/{diastolic} - Systolic in range: {systolic_in_range}, Diastolic in range: {diastolic_in_range}",
        }

    def _evaluate_score_rule(self, config: Dict, input_data: Dict) -> Dict[str, Any]:
        """Evaluate score-based rule."""
        min_score = config.get("min_score", 0)
        max_score = config.get("max_score", 1)
        score_threshold = config.get("score_threshold", 0.5)

        # Calculate score from factors
        factors = config.get("factors", [])
        total_score = 0.0
        total_weight = 0.0

        for factor in factors:
            field = factor.get("field")
            weight = factor.get("weight", 1.0)
            value = input_data.get(field, 0)

            # Simple normalization
            factor_score = self._normalize_score_value(value, factor)
            total_score += factor_score * weight
            total_weight += weight

        if total_weight > 0:
            total_score = total_score / total_weight

        matched = total_score >= score_threshold

        return {
            "matched": matched,
            "confidence": total_score,
            "score": total_score,
            "reason": f"Score {total_score:.3f} >= {score_threshold}",
        }

    def _evaluate_condition_rule(self, config: Dict, input_data: Dict) -> Dict[str, Any]:
        """Evaluate conditional rule."""
        conditions = config.get("conditions", [])
        logic = config.get("logic", "AND")  # AND or OR

        results = []
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "==")
            expected = condition.get("expected")
            actual = input_data.get(field)

            matched = self._compare_values(actual, operator, expected)
            results.append(matched)

        if logic == "AND":
            matched = all(results)
        else:  # OR
            matched = any(results)

        confidence = sum(results) / len(results) if results else 0

        return {
            "matched": matched,
            "confidence": confidence,
            "reason": f"Condition ({logic}): {results}",
        }

    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values using operator."""
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<":
            return actual < expected
        elif operator == "<=":
            return actual <= expected
        elif operator == "in":
            return actual in expected
        elif operator == "contains":
            return expected in actual if isinstance(actual, str) else False
        else:
            return False

    def _normalize_score_value(self, value: Any, factor: Dict) -> float:
        """Normalize a factor value to 0-1 range for scoring."""
        factor_type = factor.get("type", "range")

        if factor_type == "range":
            min_val = factor.get("min", 0)
            max_val = factor.get("max", 1)
            normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
            return max(0.0, min(1.0, normalized))
        elif factor_type == "binary":
            return 1.0 if value else 0.0
        else:
            return 0.5

    async def _get_vital_sign_standard(self, sign_name: str) -> Optional[VitalSignStandardModel]:
        """Get vital sign standard by name."""
        stmt = select(VitalSignStandardModel).where(
            and_(
                VitalSignStandardModel.standard_name == sign_name,
                VitalSignStandardModel.is_enabled == True
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_risk_score_rule(self, disease_code: str) -> Optional[RiskScoreRuleModel]:
        """Get risk score rule by disease code."""
        stmt = select(RiskScoreRuleModel).where(
            and_(
                RiskScoreRuleModel.disease_code == disease_code,
                RiskScoreRuleModel.is_enabled == True
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _log_execution(
        self,
        rule: RuleModel,
        context: RuleExecutionContext,
        result: Dict[str, Any],
        execution_time: int,
        error: Optional[str],
    ) -> None:
        """Log rule execution to database."""
        try:
            history = RuleExecutionHistoryModel(
                rule_id=rule.id,
                patient_id=context.patient_id,
                input_data=context.input_data,
                exec_result=result,
                matched=result.get("matched", False),
                execution_time_ms=execution_time,
                error_message=error,
                consultation_id=context.consultation_id,
                skill_id=context.skill_id,
            )
            self._session.add(history)
            await self._session.flush()
        except Exception as e:
            logger.error(f"Failed to log rule execution: {e}")


class RuleRepository:
    """
    Repository for managing rules.

    Provides CRUD operations for rules and standards.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_rule(self, rule_data: Dict[str, Any]) -> RuleModel:
        """Create a new rule."""
        rule = RuleModel(**rule_data)
        self._session.add(rule)
        await self._session.flush()
        return rule

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[RuleModel]:
        """Update an existing rule."""
        stmt = select(RuleModel).where(RuleModel.id == int(rule_id))
        result = await self._session.execute(stmt)
        rule = result.scalar_one_or_none()

        if rule:
            for key, value in updates.items():
                setattr(rule, key, value)
            await self._session.flush()

        return rule

    async def get_rule(self, rule_id: str) -> Optional[RuleModel]:
        """Get rule by ID."""
        stmt = select(RuleModel).where(RuleModel.id == int(rule_id))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_rules(
        self,
        category: Optional[str] = None,
        disease_code: Optional[str] = None,
        enabled_only: bool = True,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[RuleModel], int]:
        """List rules with filtering and pagination.

        Args:
            category: Filter by category
            disease_code: Filter by disease code
            enabled_only: Only return enabled rules
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of rules, total count)
        """
        # Build base query for counting
        count_stmt = select(func.count(RuleModel.id))
        conditions = []
        if enabled_only:
            conditions.append(RuleModel.is_enabled == True)
        if category:
            conditions.append(RuleModel.rule_category == category)
        if disease_code:
            conditions.append(RuleModel.disease_code == disease_code)

        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Build query for data
        stmt = select(RuleModel)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(RuleModel.rule_priority.desc())

        # Add pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self._session.execute(stmt)
        rules = list(result.scalars().all())

        return rules, total_count

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        stmt = select(RuleModel).where(RuleModel.id == int(rule_id))
        result = await self._session.execute(stmt)
        rule = result.scalar_one_or_none()

        if rule:
            await self._session.delete(rule)
            await self._session.flush()
            return True
        return False
