#!/usr/bin/env python3
"""
Cardiovascular Disease Risk Calculator for Chinese Adults
Based on Chinese Cardiovascular Disease Primary Prevention Risk Assessment Flowchart

流程图决策逻辑：
1. 初始高危人群判定
2. 10年ASCVD风险评估（查表法）
3. 余生风险高危判定
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Literal, Tuple


class RiskCategory(Enum):
    LOW = "low"          # 低危
    MEDIUM = "medium"    # 中危
    HIGH = "high"        # 高危
    VERY_HIGH = "very_high"  # 很高危


@dataclass
class PatientData:
    age: int
    gender: Literal["male", "female"]
    sbp: Optional[int] = None        # 收缩压 mmHg
    dbp: Optional[int] = None        # 舒张压 mmHg
    ldl_c: Optional[float] = None    # mmol/L
    tc: Optional[float] = None       # 总胆固醇 mmol/L
    hdl_c: Optional[float] = None    # mmol/L
    non_hdl_c: Optional[float] = None  # 非HDL-C mmol/L
    tg: Optional[float] = None       # 甘油三酯 mmol/L
    has_diabetes: bool = False
    diabetes_with_organ_damage: bool = False
    smoker: bool = False
    bmi: Optional[float] = None
    waist_circumference: Optional[float] = None
    family_history_premature_cvd: bool = False
    has_ckd: bool = False
    ckd_stage: Optional[int] = None
    has_established_cvd: bool = False


@dataclass
class RiskAssessmentResult:
    risk_category: RiskCategory
    risk_factors_count: int
    key_factors: list[str]
    follow_up_interval: str
    assessment_path: str  # 记录评估路径
    ten_year_risk: Optional[str] = None  # 10年ASCVD风险等级 (low/medium/high)
    ten_year_risk_range: Optional[str] = None  # 10年ASCVD风险范围 (<5%/5%-9%/≥10%)
    ten_year_cvd_risk: Optional[str] = None  # 10年心血管病发病风险等级 (基于血压分级)
    ten_year_cvd_risk_zh: Optional[str] = None  # 10年心血管病发病风险等级中文
    lifetime_risk: Optional[str] = None  # 余生风险


class CVDRiskCalculator:
    """
    中国成人心血管病一级预防风险评估计算器

    基于流程图的三层决策逻辑：
    1. 初始高危人群判定
    2. 10年ASCVD风险评估（查表法）
    3. 余生风险高危判定
    """

    # 阈值标准（来自流程图）
    AGE_DIABETES_HIGH_RISK = 40  # 糖尿病患者年龄≥40岁直接高危

    # 初始高危人群阈值
    LDL_SEVERE = 4.9      # mmol/L
    TC_SEVERE = 7.2       # mmol/L

    # 血清胆固醇分层阈值
    TC_LEVEL_1 = (3.1, 4.1)    # mmol/L
    TC_LEVEL_2 = (4.1, 5.2)
    TC_LEVEL_3 = (5.2, 7.2)

    LDL_LEVEL_1 = (1.8, 2.6)   # mmol/L
    LDL_LEVEL_2 = (2.6, 3.4)
    LDL_LEVEL_3 = (3.4, 4.9)

    # 余生风险高危阈值
    SBP_LIFETIME_HIGH = 160     # mmHg
    DBP_LIFETIME_HIGH = 100     # mmHg
    NON_HDL_LIFETIME_HIGH = 5.2 # mmol/L
    HDL_LIFETIME_LOW = 1.0      # mmol/L
    BMI_LIFETIME_HIGH = 28      # kg/m²

    # 高血压判定阈值
    BP_HYPERTENSION = (140, 90)

    # 血压分级阈值（用于10年心血管病发病风险评估）
    BP_NORMAL_HIGH = (130, 85)    # 正常高值
    BP_GRADE_1 = (140, 90)         # 高血压1级
    BP_GRADE_2 = (160, 100)        # 高血压2级

    # 危险因素年龄阈值
    AGE_MALE = 45
    AGE_FEMALE = 55
    HDL_LOW = 1.0  # mmol/L

    def calculate_risk(self, patient: PatientData) -> RiskAssessmentResult:
        """
        计算心血管风险等级（基于流程图的三层决策逻辑）
        """
        # Step 0: 已确诊心血管病（二级预防）
        if patient.has_established_cvd:
            return self._create_result(
                RiskCategory.VERY_HIGH,
                ["已确诊心血管病"],
                "已确诊心血管疾病，需要二级预防",
                "每1-3个月",
                "established_cvd"
            )

        # Step 1: 初始高危人群判定
        high_risk_result = self._check_initial_high_risk(patient)
        if high_risk_result:
            return high_risk_result

        # Step 2: 10年ASCVD风险评估（查表法）
        ten_year_result = self._assess_ten_year_risk(patient)

        # Step 3: 余生风险高危判定
        # 条件：10年风险为中危 且 年龄<55岁
        needs_lifetime_assessment = (
            ten_year_result["category"] == RiskCategory.MEDIUM and
            patient.age < 55
        )

        if needs_lifetime_assessment:
            lifetime_result = self._assess_lifetime_risk(patient, ten_year_result["risk_factors_count"])
            if lifetime_result["is_high"]:
                return self._create_result(
                    RiskCategory.VERY_HIGH,
                    lifetime_result["factors"],
                    f"余生风险高危：{', '.join(lifetime_result['factors'])}",
                    "每1-3个月",
                    "lifetime_high",
                    ten_year_risk=ten_year_result["category"].value,
                    lifetime_risk="high",
                    ten_year_cvd_risk=ten_year_result["category"].value
                )

        # 使用10年风险评估结果
        # 同时计算10年心血管病发病风险（基于血压分级+危险因素）
        ten_year_cvd_risk = self._assess_ten_year_cvd_risk(
            patient,
            ten_year_result["risk_factors_count"],
            ten_year_result["category"].value  # 传递10年ASCVD风险评估结果作为fallback
        )

        return self._create_result(
            ten_year_result["category"],
            ten_year_result["factors"],
            f"10年ASCVD风险{ten_year_result['category'].value}，危险因素{ten_year_result['risk_factors_count']}个",
            ten_year_result["follow_up"],
            "ten_year_risk",
            ten_year_risk=ten_year_result["category"].value,
            ten_year_cvd_risk=ten_year_cvd_risk
        )

    def _check_initial_high_risk(self, patient: PatientData) -> Optional[RiskAssessmentResult]:
        """
        Step 1: 初始高危人群判定

        符合以下任一条件即直接列为高危：
        1. 年龄≥40岁的糖尿病患者
        2. LDL-C≥4.9 mmol/L 或 TC≥7.2 mmol/L
        3. CKD 3/4期
        4. 严重高血压 (SBP≥180 或 DBP≥110)

        当有多个严重危险因素时，升级为很高危
        """
        factors_list = []
        is_very_high = False

        # 1. 年龄≥40岁的糖尿病患者
        if patient.has_diabetes and patient.age >= self.AGE_DIABETES_HIGH_RISK:
            factors_list.append(f"糖尿病且年龄≥{self.AGE_DIABETES_HIGH_RISK}岁")

        # 2. 严重高脂血症
        if patient.ldl_c and patient.ldl_c >= self.LDL_SEVERE:
            factors_list.append(f"LDL-C重度升高（{patient.ldl_c} mmol/L，≥{self.LDL_SEVERE}）")

        if patient.tc and patient.tc >= self.TC_SEVERE:
            factors_list.append(f"TC重度升高（{patient.tc} mmol/L，≥{self.TC_SEVERE}）")

        # 3. CKD 3/4期
        if patient.has_ckd and patient.ckd_stage and patient.ckd_stage >= 3:
            factors_list.append(f"慢性肾脏病{patient.ckd_stage}期")

        # 4. 严重高血压 (极高危指标)
        # SBP≥180 或 DBP≥110 是高血压3级的诊断标准
        if patient.sbp and patient.sbp >= 180:
            factors_list.append(f"收缩压极高（{patient.sbp} mmHg，≥{self.SBP_LIFETIME_HIGH}）")
            is_very_high = True

        if patient.dbp and patient.dbp >= 100:
            factors_list.append(f"舒张压极高（{patient.dbp} mmHg，≥{self.DBP_LIFETIME_HIGH}）")
            is_very_high = True

        # 当有≥3个危险因素或包含严重高血压时，升级为很高危
        if len(factors_list) >= 3 or is_very_high:
            # 计算10年心血管病发病风险（基于血压分级+危险因素）
            ten_year_cvd_risk = self._assess_ten_year_cvd_risk(patient, len(factors_list), "high")
            return self._create_result(
                RiskCategory.VERY_HIGH,
                factors_list,
                "很高危人群（多重危险因素叠加）",
                "每1-3个月",
                "initial_high",
                ten_year_risk="high",
                lifetime_risk="high",
                ten_year_cvd_risk=ten_year_cvd_risk
            )

        if factors_list:
            # 计算10年心血管病发病风险（基于血压分级+危险因素）
            ten_year_cvd_risk = self._assess_ten_year_cvd_risk(patient, len(factors_list), "high")
            return self._create_result(
                RiskCategory.HIGH,
                factors_list,
                "初始高危人群",
                "每1-3个月",
                "initial_high",
                ten_year_cvd_risk=ten_year_cvd_risk
            )

        return None

    def _assess_ten_year_risk(self, patient: PatientData) -> dict:
        """
        Step 2: 10年ASCVD风险评估（查表法）

        根据以下因素查表确定风险等级：
        1. 血清胆固醇水平分层（TC或LDL-C）
        2. 危险因素数量（0-3个：吸烟、低HDL-C、年龄）
        3. 血压状态（无高血压/有高血压）
        """
        # 确定胆固醇水平分层
        cholesterol_level = self._get_cholesterol_level(patient)

        # 计算查表用的危险因素数量（不包括高血压）
        table_risk_factors = self._count_table_risk_factors(patient)

        # 判断是否有高血压
        has_hypertension = self._has_hypertension(patient)

        # 查表确定10年风险等级
        category, factors = self._lookup_risk_table(
            cholesterol_level,
            table_risk_factors["count"],
            has_hypertension,
            table_risk_factors["factors"]
        )

        # 确定随访间隔
        follow_up_map = {
            RiskCategory.LOW: "每年",
            RiskCategory.MEDIUM: "每6个月",
            RiskCategory.HIGH: "每3-6个月"
        }

        return {
            "category": category,
            "risk_factors_count": table_risk_factors["count"],
            "factors": factors,
            "follow_up": follow_up_map[category],
            "cholesterol_level": cholesterol_level,
            "has_hypertension": has_hypertension
        }

    def _get_cholesterol_level(self, patient: PatientData) -> int:
        """
        确定血清胆固醇水平分层（1-3级，按流程图）

        优先使用LDL-C，其次使用TC

        胆固醇分层标准：
        | 分层 | TC (mmol/L) | LDL-C (mmol/L) |
        |:----:|:------------:|:---------------:|
        | 1级  | 3.1-4.1      | 1.8-2.6         |
        | 2级  | 4.1-5.2      | 2.6-3.4         |
        | 3级  | 5.2-7.2      | 3.4-4.9         |

        注：≥7.2或≥4.9的情况已在初始高危判定中处理
        """
        # 优先使用LDL-C
        if patient.ldl_c:
            if patient.ldl_c < self.LDL_LEVEL_1[1]:  # <2.6
                return 1
            elif patient.ldl_c < self.LDL_LEVEL_2[1]:  # <3.4
                return 2
            else:  # 3.4-4.9
                return 3

        # 其次使用TC
        if patient.tc:
            if patient.tc < self.TC_LEVEL_1[1]:  # <4.1
                return 1
            elif patient.tc < self.TC_LEVEL_2[1]:  # <5.2
                return 2
            else:  # 5.2-7.2
                return 3

        # 无数据时默认为2级
        return 2

    def _count_table_risk_factors(self, patient: PatientData) -> dict:
        """
        计算查表用的危险因素数量（0-3个）

        包括：吸烟、低HDL-C、年龄（男≥45岁，女≥55岁）
        注意：不包括高血压（高血压作为单独的查表维度）
        """
        factors = []
        count = 0

        # 1. 吸烟
        if patient.smoker:
            factors.append("吸烟")
            count += 1

        # 2. 低HDL-C
        if patient.hdl_c and patient.hdl_c < self.HDL_LOW:
            factors.append(f"HDL-C低（{patient.hdl_c} mmol/L）")
            count += 1

        # 3. 年龄
        age_threshold = self.AGE_MALE if patient.gender == "male" else self.AGE_FEMALE
        if patient.age >= age_threshold:
            factors.append(f"年龄≥{age_threshold}岁")
            count += 1

        return {"count": min(count, 3), "factors": factors}  # 最多3个

    def _has_hypertension(self, patient: PatientData) -> bool:
        """判断是否有高血压（SBP≥140 或 DBP≥90）"""
        if patient.sbp and patient.dbp:
            return patient.sbp >= self.BP_HYPERTENSION[0] or patient.dbp >= self.BP_HYPERTENSION[1]
        return False

    def _lookup_risk_table(self, cholesterol_level: int, risk_factors: int,
                          has_hypertension: bool, factors: list) -> Tuple[RiskCategory, list]:
        """
        查表确定10年ASCVD风险等级（按流程图查表法）

        风险分层（10年ASCVD风险）：
        - 低危：<5%
        - 中危：5%-9%
        - 高危：≥10%

        查表参数：
        - 胆固醇水平分层（1-3级）
          1级：TC 3.1-4.1 或 LDL-C 1.8-2.6 mmol/L
          2级：TC 4.1-5.2 或 LDL-C 2.6-3.4 mmol/L
          3级：TC 5.2-7.2 或 LDL-C 3.4-4.9 mmol/L
        - 危险因素数量（0-3个）：吸烟、低HDL-C、年龄（男≥45/女≥55）
        - 高血压状态：无/有

        查表规则（根据流程图）：

        表1：无高血压人群
        | 因素数 | 1级 | 2级 | 3级 |
        |--------|-----|-----|-----|
        | 0个    | 低危 | 低危 | 低危 |
        | 1个    | 低危 | 低危 | 中危 |
        | 2个    | 中危 | 中危 | 中危 |
        | 3个    | 中危 | 中危 | 高危 |

        表2：有高血压人群
        | 因素数 | 1级 | 2级 | 3级 |
        |--------|-----|-----|-----|
        | 0个    | 低危 | 中危 | 中危 |
        | 1个    | 中危 | 中危 | 中危 |
        | 2个    | 中危 | 中危 | 高危 |
        | 3个    | 高危 | 高危 | 高危 |
        """
        all_factors = factors.copy()

        # 场景1：无高血压
        if not has_hypertension:
            if risk_factors == 0:
                return RiskCategory.LOW, all_factors
            elif risk_factors == 1:
                # 胆固醇1-2层=低危，3层=中危
                if cholesterol_level <= 2:
                    return RiskCategory.LOW, all_factors
                else:  # cholesterol_level == 3
                    return RiskCategory.MEDIUM, all_factors
            elif risk_factors == 2:
                return RiskCategory.MEDIUM, all_factors
            else:  # risk_factors == 3
                if cholesterol_level <= 2:
                    return RiskCategory.MEDIUM, all_factors
                else:  # cholesterol_level == 3
                    return RiskCategory.HIGH, all_factors

        # 场景2：有高血压
        else:
            all_factors.insert(0, "高血压")  # 高血压放在首位

            if risk_factors == 0:
                # 胆固醇1层=低危，2-3层=中危
                if cholesterol_level == 1:
                    return RiskCategory.LOW, all_factors
                else:  # cholesterol_level 2 or 3
                    return RiskCategory.MEDIUM, all_factors
            elif risk_factors == 1:
                return RiskCategory.MEDIUM, all_factors
            elif risk_factors == 2:
                # 胆固醇1-2层=中危，3层=高危
                if cholesterol_level <= 2:
                    return RiskCategory.MEDIUM, all_factors
                else:  # cholesterol_level == 3
                    return RiskCategory.HIGH, all_factors
            else:  # risk_factors == 3
                return RiskCategory.HIGH, all_factors

        # 默认中危
        return RiskCategory.MEDIUM, all_factors

    def _assess_lifetime_risk(self, patient: PatientData, ten_year_factors: int) -> dict:
        """
        Step 3: 余生风险高危判定

        触发条件：10年风险为中危 且 年龄<55岁

        心血管病余生风险为高危的条件（需具备以下**任意2项及以上**）：

        | 指标 | 阈值 |
        |:----|:----|
        | 收缩压 | ≥160 mmHg |
        | 舒张压 | ≥100 mmHg |
        | 非HDL-C | ≥5.2 mmol/L |
        | HDL-C | <1.0 mmol/L |
        | BMI | ≥28 kg/m² |
        | 吸烟 | 是 |
        """
        factors = []

        # 1. 极度高血压
        if patient.sbp and patient.sbp >= self.SBP_LIFETIME_HIGH:
            factors.append(f"收缩压极高（{patient.sbp} mmHg，≥{self.SBP_LIFETIME_HIGH}）")

        if patient.dbp and patient.dbp >= self.DBP_LIFETIME_HIGH:
            factors.append(f"舒张压极高（{patient.dbp} mmHg，≥{self.DBP_LIFETIME_HIGH}）")

        # 2. 非HDL-C极高
        if patient.non_hdl_c and patient.non_hdl_c >= self.NON_HDL_LIFETIME_HIGH:
            factors.append(f"非HDL-C极高（{patient.non_hdl_c} mmol/L，≥{self.NON_HDL_LIFETIME_HIGH}）")

        # 3. HDL-C过低
        if patient.hdl_c and patient.hdl_c < self.HDL_LIFETIME_LOW:
            factors.append(f"HDL-C过低（{patient.hdl_c} mmol/L，<{self.HDL_LIFETIME_LOW}）")

        # 4. 肥胖
        if patient.bmi and patient.bmi >= self.BMI_LIFETIME_HIGH:
            factors.append(f"肥胖（BMI {patient.bmi}，≥{self.BMI_LIFETIME_HIGH}）")

        # 5. 吸烟
        if patient.smoker:
            factors.append("吸烟")

        return {
            "is_high": len(factors) >= 2,  # 需具备任意2项及以上
            "factors": factors
        }

    def _assess_ten_year_cvd_risk(self, patient: PatientData, table_risk_factors_count: int, ascvd_risk_fallback: str = "medium") -> str:
        """
        评估10年心血管病发病风险（基于血压分级+危险因素数量）

        高危判定标准：
        1. 正常高值血压（SBP 130-139 或 DBP 85-89）+ 3个危险因素
        2. 高血压1级（SBP 140-159 或 DBP 90-99）+ 2个危险因素
        3. 高血压2级及以上（SBP ≥160 或 DBP ≥100）+ 1个危险因素

        非高危情况：参考10年ASCVD风险评估结果

        参数:
            ascvd_risk_fallback: 10年ASCVD风险评估结果，用于非高危情况的fallback
        注意：这里的危险因素数量包括高血压本身
        """
        sbp = patient.sbp or 0
        dbp = patient.dbp or 0

        # 判定血压分级
        bp_grade = None
        has_hypertension = sbp >= 140 or dbp >= 90

        if sbp >= 160 or dbp >= 100:
            bp_grade = 2  # 高血压2级及以上
        elif sbp >= 140 or dbp >= 90:
            bp_grade = 1  # 高血压1级
        elif sbp >= 130 or dbp >= 85:
            bp_grade = 0  # 正常高值

        # 计算总危险因素数量（包括高血压）
        # table_risk_factors_count不包括高血压，所以如果有高血压则+1
        if has_hypertension:
            total_risk_factors = table_risk_factors_count + 1
        else:
            total_risk_factors = table_risk_factors_count

        # 根据血压分级和总危险因素数量判定是否高危
        if bp_grade == 0 and total_risk_factors >= 3:
            # 正常高值 + 3个危险因素 = 高危
            return "high"
        elif bp_grade == 1 and total_risk_factors >= 2:
            # 高血压1级 + 2个危险因素 = 高危
            return "high"
        elif bp_grade == 2 and total_risk_factors >= 1:
            # 高血压2级及以上 + 1个危险因素 = 高危
            return "high"

        # 其余情况：参考10年ASCVD风险评估结果
        return ascvd_risk_fallback

    def _create_result(self, category: RiskCategory, factors: list,
                       description: str, follow_up: str, path: str,
                       ten_year_risk: Optional[str] = None,
                       lifetime_risk: Optional[str] = None,
                       ten_year_cvd_risk: Optional[str] = None) -> RiskAssessmentResult:
        """创建风险评估结果"""
        # 根据ten_year_risk计算风险范围
        ten_year_risk_range = None
        if ten_year_risk:
            risk_range_map = {
                "low": "<5%",
                "medium": "5%-9%",
                "high": "≥10%"
            }
            ten_year_risk_range = risk_range_map.get(ten_year_risk)

        # 根据ten_year_cvd_risk计算中文描述
        ten_year_cvd_risk_zh = None
        if ten_year_cvd_risk:
            risk_zh_map = {
                "low": "低危",
                "medium": "中危",
                "high": "高危"
            }
            ten_year_cvd_risk_zh = risk_zh_map.get(ten_year_cvd_risk)

        return RiskAssessmentResult(
            risk_category=category,
            risk_factors_count=len(factors),
            key_factors=factors,
            follow_up_interval=follow_up,
            assessment_path=path,
            ten_year_risk=ten_year_risk,
            ten_year_risk_range=ten_year_risk_range,
            ten_year_cvd_risk=ten_year_cvd_risk,
            ten_year_cvd_risk_zh=ten_year_cvd_risk_zh,
            lifetime_risk=lifetime_risk
        )


def main():
    """示例用法"""
    import sys
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    calculator = CVDRiskCalculator()

    # 示例1：符合初始高危（LDL-C≥4.9）
    patient1 = PatientData(
        age=45,
        gender="male",
        sbp=185,
        dbp=105,
        ldl_c=16.0,
        tc=12.0,
        has_diabetes=False
    )

    result1 = calculator.calculate_risk(patient1)
    print("="*60)
    print("患者1：45岁男性，LDL-C 16 mmol/L，TC 12 mmol/L")
    print(f"风险等级: {result1.risk_category.value}")
    print(f"评估路径: {result1.assessment_path}")
    print(f"关键因素: {result1.key_factors}")
    print(f"随访: {result1.follow_up_interval}")
    print()

    # 示例2：需要10年风险查表
    patient2 = PatientData(
        age=50,
        gender="male",
        sbp=135,  # 无高血压
        dbp=85,
        ldl_c=3.2,
        has_diabetes=False,
        smoker=True
    )

    result2 = calculator.calculate_risk(patient2)
    print("="*60)
    print("患者2：50岁男性，血压正常，LDL-C 3.2，吸烟")
    print(f"风险等级: {result2.risk_category.value}")
    print(f"评估路径: {result2.assessment_path}")
    print(f"10年风险: {result2.ten_year_risk}")
    print(f"关键因素: {result2.key_factors}")
    print()

    # 示例3：余生风险高危（收缩压≥160）
    patient3 = PatientData(
        age=50,
        gender="male",
        sbp=170,  # 极度高血压
        dbp=95,
        ldl_c=4.0,  # 胆固醇水平3级
        tc=6.0,
        has_diabetes=False,
        smoker=True,
        bmi=30  # BMI≥28
    )

    result3 = calculator.calculate_risk(patient3)
    print("="*60)
    print("患者3：50岁男性，血压170/95，LDL-C 4.0，吸烟，BMI 30")
    print(f"风险等级: {result3.risk_category.value}")
    print(f"评估路径: {result3.assessment_path}")
    print(f"10年风险: {result3.ten_year_risk}")
    print(f"余生风险: {result3.lifetime_risk}")
    print(f"关键因素: {result3.key_factors}")
    print()

    # 示例4：糖尿病≥40岁
    patient4 = PatientData(
        age=42,
        gender="female",
        sbp=130,
        dbp=80,
        has_diabetes=True
    )

    result4 = calculator.calculate_risk(patient4)
    print("="*60)
    print("患者4：42岁女性，糖尿病患者")
    print(f"风险等级: {result4.risk_category.value}")
    print(f"评估路径: {result4.assessment_path}")
    print(f"关键因素: {result4.key_factors}")
    print()


if __name__ == "__main__":
    main()
