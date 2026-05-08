#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Population Classification - Health Group Assessment

Classifies users into four health groups: 健康 / 亚健康 / 慢病 / 重症
based on health indicators, vital signs, and medical history.

Input: patient data in multiple formats (flat dict / agent nested / JSON file / natural text)
Output: structured JSON with population group, score, basis, and recommendations
"""

import json
import sys
import argparse
import re
import math
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple


# ---------------------------------------------------------------------------
# Indicator scoring configuration
# ---------------------------------------------------------------------------

# Each indicator: (field_name, thresholds)
# thresholds: list of (lower_bound_inclusive, score, label_zh)
# evaluated top-to-bottom, first match wins; if value < first bound -> normal (0)
INDICATOR_SCORING: Dict[str, List[Tuple[float, int, str]]] = {
    # BMI
    "bmi": [
        (32.0, 20, "BMI重度肥胖({value})"),
        (28.0, 14, "BMI肥胖({value})"),
        (24.0, 6,  "BMI超重({value})"),
        (18.5, 0,  ""),  # normal range marker
    ],
    # Systolic blood pressure (mmHg)
    "sbp": [
        (180, 20, "收缩压极高({value}mmHg)"),
        (160, 12, "收缩压偏高({value}mmHg)"),
        (140, 6,  "收缩压轻度偏高({value}mmHg)"),
        (90,  0,  ""),
    ],
    # Diastolic blood pressure (mmHg)
    "dbp": [
        (110, 18, "舒张压极高({value}mmHg)"),
        (100, 12, "舒张压偏高({value}mmHg)"),
        (90,  6,  "舒张压轻度偏高({value}mmHg)"),
        (60,  0,  ""),
    ],
    # Fasting glucose (mmol/L)
    "fasting_glucose": [
        (11.1, 20, "空腹血糖极高({value}mmol/L)"),
        (7.0,  12, "空腹血糖偏高({value}mmol/L)"),
        (6.1,  6,  "空腹血糖受损({value}mmol/L)"),
        (3.9,  0,  ""),
    ],
    # HbA1c (%)
    "hba1c": [
        (9.0,  18, "糖化血红蛋白控制极差({value}%)"),
        (7.0,  10, "糖化血红蛋白偏高({value}%)"),
        (6.5,  5,  "糖化血红蛋白临界({value}%)"),
        (0,    0,  ""),
    ],
    # Total cholesterol (mmol/L)
    "tc": [
        (6.2, 12, "总胆固醇极高({value}mmol/L)"),
        (5.2, 6,  "总胆固醇偏高({value}mmol/L)"),
        (0,   0,  ""),
    ],
    # LDL-C (mmol/L)
    "ldl_c": [
        (4.9, 14, "低密度脂蛋白极高({value}mmol/L)"),
        (3.4, 8,  "低密度脂蛋白偏高({value}mmol/L)"),
        (0,   0,  ""),
    ],
    # HDL-C (mmol/L) — lower is worse
    "hdl_c": [
        (0,   0,  ""),
        (0.8, 8,  "高密度脂蛋白极低({value}mmol/L)"),
        (1.0, 4,  "高密度脂蛋白偏低({value}mmol/L)"),
    ],
    # Triglycerides (mmol/L)
    "tg": [
        (5.6, 14, "甘油三酯极高({value}mmol/L)"),
        (2.3, 8,  "甘油三酯偏高({value}mmol/L)"),
        (1.7, 4,  "甘油三酯临界({value}mmol/L)"),
        (0,   0,  ""),
    ],
    # Uric acid (μmol/L)
    "uric_acid": [
        (600, 10, "尿酸极高({value}μmol/L)"),
        (480, 6,  "尿酸偏高({value}μmol/L)"),
        (420, 4,  "尿酸临界({value}μmol/L)"),
        (0,   0,  ""),
    ],
    # ALT (U/L)
    "alt": [
        (120, 12, "谷丙转氨酶极高({value}U/L)"),
        (80,  8,  "谷丙转氨酶偏高({value}U/L)"),
        (40,  4,  "谷丙转氨酶轻度偏高({value}U/L)"),
        (0,   0,  ""),
    ],
    # Creatinine (μmol/L)
    "creatinine": [
        (442, 18, "肌酐极高({value}μmol/L)"),
        (177, 12, "肌酐偏高({value}μmol/L)"),
        (133, 6,  "肌酐轻度偏高({value}μmol/L)"),
        (0,   0,  ""),
    ],
}

# Disease labels that directly indicate chronic conditions
CHRONIC_DISEASE_KEYWORDS = {
    "hypertension": ("高血压", 15),
    "diabetes": ("糖尿病", 15),
    "hyperlipidemia": ("高血脂", 10),
    "hyperuricemia": ("高尿酸", 8),
    "gout": ("痛风", 10),
    "copd": ("慢性阻塞性肺疾病", 12),
    "kidney_disease": ("肾病", 15),
    "liver_disease": ("肝病", 10),
    "cancer": ("癌症", 25),
    "heart_disease": ("心脏病", 20),
    "stroke": ("中风", 25),
}

# Group thresholds
GROUP_THRESHOLDS = [
    (81, "重症"),
    (51, "慢病"),
    (21, "亚健康"),
    (0,  "健康"),
]

# Follow-up intervals by group
FOLLOW_UP_MAP = {
    "健康": "每年",
    "亚健康": "每6个月",
    "慢病": "每3个月",
    "重症": "每月",
}

# Chinese labels for recommended data items
RECOMMENDED_LABELS = {
    "sbp": "血压", "dbp": "血压",
    "fasting_glucose": "空腹血糖", "hba1c": "糖化血红蛋白",
    "tc": "总胆固醇", "tg": "甘油三酯", "ldl_c": "低密度脂蛋白",
    "hdl_c": "高密度脂蛋白", "uric_acid": "血尿酸", "bmi": "BMI",
    "alt": "谷丙转氨酶", "creatinine": "肌酐",
}

# Abnormal indicator reference ranges (for structured_result)
ABNORMAL_RANGES = {
    "bmi":  {"name": "BMI",   "unit": "kg/m²",  "ref": "18.5-23.9"},
    "sbp":  {"name": "收缩压", "unit": "mmHg",   "ref": "<140"},
    "dbp":  {"name": "舒张压", "unit": "mmHg",   "ref": "<90"},
    "fasting_glucose": {"name": "空腹血糖", "unit": "mmol/L", "ref": "3.9-6.1"},
    "hba1c": {"name": "糖化血红蛋白", "unit": "%", "ref": "<6.5"},
    "tc":   {"name": "总胆固醇", "unit": "mmol/L", "ref": "<5.2"},
    "ldl_c": {"name": "低密度脂蛋白", "unit": "mmol/L", "ref": "<3.4"},
    "hdl_c": {"name": "高密度脂蛋白", "unit": "mmol/L", "ref": "≥1.0"},
    "tg":   {"name": "甘油三酯", "unit": "mmol/L", "ref": "<1.7"},
    "uric_acid": {"name": "血尿酸", "unit": "μmol/L", "ref": "<420"},
    "alt":  {"name": "谷丙转氨酶", "unit": "U/L", "ref": "<40"},
    "creatinine": {"name": "肌酐", "unit": "μmol/L", "ref": "44-133"},
}


class PopulationClassifier:
    """Health population group classifier."""

    def extract_patient_data(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse patient data from various input formats.

        Supported formats:
        1. JSON file path
        2. JSON string
        3. Python dict (flat or nested)
        4. Agent nested format (patient_data, vital_signs, medical_history)
        5. Natural text description
        """
        if isinstance(input_data, str):
            input_path = Path(input_data)
            if input_path.exists():
                with open(input_path, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
            else:
                try:
                    input_data = json.loads(input_data)
                except json.JSONDecodeError:
                    return self._parse_natural_text(input_data)

        if isinstance(input_data, dict):
            if 'patient_data' in input_data or 'vital_signs' in input_data:
                return self._flatten_agent_format(input_data)
            if 'health_metrics' in input_data or 'patient_info' in input_data:
                return self._flatten_health_metrics_format(input_data)
            if 'user_input' in input_data:
                result = {}
                if input_data.get('user_input'):
                    natural_data = self._parse_natural_text(input_data['user_input'])
                    result.update(natural_data)
                for key, value in input_data.items():
                    if key != 'user_input' and value is not None:
                        result[key] = value
                return result
            return self._normalize_flat_fields(input_data)

        return {}

    # Field aliases: common external names → internal names used by scoring
    _FIELD_ALIASES = {
        "systolic_bp": "sbp", "systolicPressure": "sbp",
        "diastolic_bp": "dbp", "diastolicPressure": "dbp",
        "total_cholesterol": "tc", "totalCholesterol": "tc",
        "diseaseLabels": "disease_labels",
        "diseaseHistory": "disease_history",
    }

    def _normalize_flat_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize common field aliases to internal field names."""
        result = dict(data)
        for alias, internal in self._FIELD_ALIASES.items():
            if alias in result and internal not in result:
                result[internal] = result[alias]
        return result

    def _flatten_agent_format(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten agent nested format to flat dict."""
        patient_data = {}

        if 'patient_data' in input_data:
            pd = input_data['patient_data']
            if 'basic_info' in pd:
                bi = pd['basic_info']
                age = bi.get('age')
                if age is not None:
                    try:
                        patient_data['age'] = int(str(age).strip())
                    except (ValueError, TypeError):
                        patient_data['age'] = age
            else:
                age = pd.get('age')
                if age is not None:
                    try:
                        patient_data['age'] = int(str(age).strip())
                    except (ValueError, TypeError):
                        patient_data['age'] = age
                patient_data['gender'] = pd.get('gender')
                patient_data['height'] = pd.get('height')
                patient_data['weight'] = pd.get('weight')

        if 'vital_signs' in input_data:
            vs = input_data['vital_signs']
            field_mapping = {
                'systolic_bp': 'sbp', 'diastolic_bp': 'dbp',
                'total_cholesterol': 'tc', 'ldl_c': 'ldl_c',
                'hdl_c': 'hdl_c', 'tg': 'tg',
                'fasting_glucose': 'fasting_glucose', 'hba1c': 'hba1c',
                'bmi': 'bmi', 'uric_acid': 'uric_acid',
                'creatinine': 'creatinine', 'alt': 'alt',
            }
            for agent_field, internal_field in field_mapping.items():
                if agent_field in vs and vs[agent_field] is not None:
                    patient_data[internal_field] = vs[agent_field]

        if 'medical_history' in input_data:
            mh = input_data['medical_history']
            # Extract disease labels
            disease_labels = mh.get('disease_labels', [])
            if disease_labels:
                patient_data['disease_labels'] = disease_labels
            # Also check for individual disease flags
            for flag in ['has_diabetes', 'has_hypertension', 'has_hyperlipidemia',
                         'has_ckd', 'has_established_cvd', 'smoker']:
                if mh.get(flag):
                    patient_data[flag] = True

        # Derive BMI from height/weight if not present
        if 'bmi' not in patient_data:
            h = patient_data.get('height')
            w = patient_data.get('weight')
            if h and w and h > 0:
                patient_data['bmi'] = round(w / ((h / 100) ** 2), 1)

        # Parse gender from user_input fallback
        if 'user_input' in input_data and input_data['user_input']:
            user_text = input_data['user_input']
            if not patient_data.get('gender'):
                if any(w in user_text for w in ['男性', '男', 'male', '先生', '他']):
                    patient_data['gender'] = 'male'
                elif any(w in user_text for w in ['女性', '女', 'female', '女士', '她']):
                    patient_data['gender'] = 'female'
            natural_data = self._parse_natural_text(user_text)
            for key, value in natural_data.items():
                if key not in patient_data or patient_data[key] is None:
                    patient_data[key] = value

        return patient_data

    def _flatten_health_metrics_format(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten health_metrics format to flat dict."""
        patient_data = {}

        if 'patient_info' in input_data:
            pi = input_data['patient_info']
            age = pi.get('age')
            if age is not None:
                try:
                    patient_data['age'] = int(age)
                except (ValueError, TypeError):
                    patient_data['age'] = age
            patient_data['gender'] = pi.get('gender')

        if 'health_metrics' in input_data:
            hm = input_data['health_metrics']
            if 'blood_pressure' in hm:
                bp = hm['blood_pressure']
                patient_data['sbp'] = bp.get('systolic')
                patient_data['dbp'] = bp.get('diastolic')
            if 'blood_glucose' in hm:
                bg = hm['blood_glucose']
                patient_data['fasting_glucose'] = bg.get('fasting')
                patient_data['hba1c'] = bg.get('hba1c')
            if 'blood_lipid' in hm:
                bl = hm['blood_lipid']
                patient_data['tc'] = bl.get('tc')
                patient_data['tg'] = bl.get('tg')
                patient_data['ldl_c'] = bl.get('ldl_c')
                patient_data['hdl_c'] = bl.get('hdl_c')
            if 'uric_acid' in hm:
                patient_data['uric_acid'] = hm['uric_acid']
            if 'bmi' in hm:
                bmi_data = hm['bmi']
                if isinstance(bmi_data, dict):
                    patient_data['bmi'] = bmi_data.get('value')
                else:
                    patient_data['bmi'] = bmi_data
            if 'basic' in hm:
                basic = hm['basic']
                if 'height' in basic:
                    patient_data['height'] = basic['height']
                if 'weight' in basic:
                    patient_data['weight'] = basic['weight']

        # Derive BMI
        if 'bmi' not in patient_data:
            h = patient_data.get('height')
            w = patient_data.get('weight')
            if h and w and h > 0:
                patient_data['bmi'] = round(w / ((h / 100) ** 2), 1)

        return patient_data

    def _parse_natural_text(self, text: str) -> Dict[str, Any]:
        """Extract patient data from natural text."""
        data = {}

        # Age
        for pat in [r'(\d+)\s*岁', r'(\d+)\s*yo\b', r'age\s*[:：]?\s*(\d+)']:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data['age'] = int(m.group(1))
                break

        # Gender
        if any(w in text for w in ['男性', '男', 'male', '先生']):
            data['gender'] = 'male'
        elif any(w in text for w in ['女性', '女', 'female', '女士']):
            data['gender'] = 'female'

        # Blood pressure
        for pat in [r'BP\s*[:：]?\s*(\d{2,3})[\/\-](\d{2,3})',
                    r'(\d{2,3})[\/\-](\d{2,3})',
                    r'收缩压\s*(\d{2,3})[^\d]*舒张压\s*(\d{2,3})',
                    r'血压\s*[:：]?\s*(\d{2,3})[\/\-](\d{2,3})']:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data['sbp'] = int(m.group(1))
                data['dbp'] = int(m.group(2))
                break

        # BMI
        m = re.search(r'bmi\s*[:：]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if m:
            data['bmi'] = float(m.group(1))

        # Height / weight
        m = re.search(r'身高\s*[:：]?\s*(\d+\.?\d*)\s*cm', text)
        if m:
            data['height'] = float(m.group(1))
        m = re.search(r'体重\s*[:：]?\s*(\d+\.?\d*)\s*kg', text)
        if m:
            data['weight'] = float(m.group(1))

        # Diabetes
        if any(w in text for w in ['糖尿病', 'diabetes', 'dm']):
            data['has_diabetes'] = True

        return data

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_indicators(self, patient_data: Dict[str, Any]) -> Tuple[int, List[str], List[str]]:
        """
        Score each available indicator.

        Returns (total_score, basis_list, risk_indicator_names).
        """
        total_score = 0
        basis: List[str] = []
        risk_indicators: List[str] = []

        for field, thresholds in INDICATOR_SCORING.items():
            value = patient_data.get(field)
            if value is None:
                continue
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            scored = False
            if field == "hdl_c":
                # HDL-C: lower is worse — special handling
                # thresholds are ordered: (0,0,""), (0.8,8,...), (1.0,4,...)
                # We check from the end (highest threshold that value is below)
                for lower, score, label in thresholds[1:]:
                    if value < lower and score > 0:
                        total_score += score
                        basis.append(label.format(value=value))
                        risk_indicators.append(field)
                        scored = True
                        break
            else:
                # Normal: value >= lower_bound -> applies
                for lower, score, label in thresholds:
                    if value >= lower and score > 0:
                        total_score += score
                        basis.append(label.format(value=value))
                        risk_indicators.append(field)
                        scored = True
                        break

        return total_score, basis, risk_indicators

    def _score_diseases(self, patient_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Score based on known disease labels and history flags.

        Returns (additional_score, basis_list).
        """
        score = 0
        basis: List[str] = []
        seen = set()

        # Check disease_labels list
        disease_labels = patient_data.get('disease_labels', [])
        if isinstance(disease_labels, list):
            for label in disease_labels:
                label_str = str(label).lower().strip()
                for key, (zh_name, pts) in CHRONIC_DISEASE_KEYWORDS.items():
                    if key not in seen and (key in label_str or zh_name in str(label)):
                        score += pts
                        basis.append(f"已确诊{zh_name}")
                        seen.add(key)

        # Check individual boolean flags
        flag_map = {
            'has_diabetes': ('糖尿病', 15),
            'has_hypertension': ('高血压', 15),
            'has_hyperlipidemia': ('高血脂', 10),
            'has_ckd': ('慢性肾病', 15),
            'has_established_cvd': ('心血管病', 20),
        }
        for flag, (zh_name, pts) in flag_map.items():
            if patient_data.get(flag) and zh_name not in {b.replace("已确诊", "") for b in basis}:
                score += pts
                basis.append(f"已确诊{zh_name}")

        # Derive disease from lab values if not already flagged
        fg = patient_data.get('fasting_glucose')
        if fg and fg >= 7.0 and '糖尿病' not in {b.replace("已确诊", "") for b in basis}:
            score += 10
            basis.append(f"疑似糖尿病(空腹血糖{fg}mmol/L)")

        return score, basis

    def _determine_groups(self, total_score: int) -> Tuple[List[str], str]:
        """Map score to a list of applicable group names and the primary follow-up interval.

        A person can belong to multiple groups. For example, if score >= 81
        (重症), they are also classified as 慢病, 亚健康 because 重症 implies
        all the lower-severity categories as well.

        Returns (groups_list, primary_follow_up) where primary_follow_up
        corresponds to the highest-severity group.
        """
        groups: List[str] = []
        primary_group = "健康"
        for threshold, group in GROUP_THRESHOLDS:
            if total_score >= threshold:
                groups.append(group)
                if primary_group == "健康":
                    primary_group = group

        if not groups:
            groups = ["健康"]

        return groups, FOLLOW_UP_MAP[primary_group]

    # ------------------------------------------------------------------
    # Output builders
    # ------------------------------------------------------------------

    def _build_abnormal_indicators(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build abnormal indicators list for structured_result."""
        abnormal = []

        # BMI
        bmi = patient_data.get('bmi')
        if bmi:
            bmi = float(bmi)
            if bmi >= 28:
                abnormal.append({"name": "BMI", "value": bmi, "unit": "kg/m²",
                                 "reference_range": "18.5-23.9", "severity": "肥胖", "clinical_note": "BMI≥28"})
            elif bmi >= 24:
                abnormal.append({"name": "BMI", "value": bmi, "unit": "kg/m²",
                                 "reference_range": "18.5-23.9", "severity": "超重", "clinical_note": "BMI≥24"})

        # Blood pressure
        sbp = patient_data.get('sbp')
        if sbp and float(sbp) >= 140:
            abnormal.append({"name": "收缩压", "value": sbp, "unit": "mmHg",
                             "reference_range": "<140", "severity": "偏高", "clinical_note": "高血压"})
        dbp = patient_data.get('dbp')
        if dbp and float(dbp) >= 90:
            abnormal.append({"name": "舒张压", "value": dbp, "unit": "mmHg",
                             "reference_range": "<90", "severity": "偏高", "clinical_note": "高血压"})

        # Glucose
        fg = patient_data.get('fasting_glucose')
        if fg and float(fg) >= 6.1:
            sev = "偏高" if float(fg) >= 7.0 else "临界"
            abnormal.append({"name": "空腹血糖", "value": fg, "unit": "mmol/L",
                             "reference_range": "3.9-6.1", "severity": sev, "clinical_note": "血糖异常"})

        # HbA1c
        hba1c = patient_data.get('hba1c')
        if hba1c and float(hba1c) >= 6.5:
            abnormal.append({"name": "糖化血红蛋白", "value": hba1c, "unit": "%",
                             "reference_range": "<6.5", "severity": "偏高", "clinical_note": "血糖控制不佳"})

        # Lipids
        tc = patient_data.get('tc')
        if tc and float(tc) >= 5.2:
            abnormal.append({"name": "总胆固醇", "value": tc, "unit": "mmol/L",
                             "reference_range": "<5.2", "severity": "偏高", "clinical_note": "血脂异常"})
        ldl = patient_data.get('ldl_c')
        if ldl and float(ldl) >= 3.4:
            abnormal.append({"name": "低密度脂蛋白", "value": ldl, "unit": "mmol/L",
                             "reference_range": "<3.4", "severity": "偏高", "clinical_note": "血脂异常"})
        hdl = patient_data.get('hdl_c')
        if hdl and float(hdl) < 1.0:
            abnormal.append({"name": "高密度脂蛋白", "value": hdl, "unit": "mmol/L",
                             "reference_range": "≥1.0", "severity": "偏低", "clinical_note": "血脂异常"})
        tg = patient_data.get('tg')
        if tg and float(tg) >= 1.7:
            abnormal.append({"name": "甘油三酯", "value": tg, "unit": "mmol/L",
                             "reference_range": "<1.7", "severity": "偏高", "clinical_note": "血脂异常"})

        # Uric acid
        ua = patient_data.get('uric_acid')
        if ua and float(ua) >= 420:
            abnormal.append({"name": "血尿酸", "value": ua, "unit": "μmol/L",
                             "reference_range": "<420", "severity": "偏高", "clinical_note": "高尿酸血症"})

        return abnormal

    def _build_recommended_data(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build recommended data collection list."""
        recommended = []
        for field, label in RECOMMENDED_LABELS.items():
            if field not in patient_data or patient_data[field] is None:
                recommended.append({
                    "item": label,
                    "reason": f"缺少{label}数据，建议补充检测",
                    "priority": "recommended"
                })
        return recommended

    def _build_intervention_prescriptions(self, group: str) -> List[Dict[str, Any]]:
        """Build intervention prescriptions based on group."""
        prescriptions = [
            {"type": "diet", "title": "饮食处方",
             "content": ["均衡饮食，控制钠盐摄入<6g/天", "增加蔬菜水果", "减少高脂高糖食物"],
             "priority": "high" if group in ("慢病", "重症") else "medium"},
            {"type": "exercise", "title": "运动处方",
             "content": ["每周至少150分钟中等强度有氧运动（快走、游泳、骑车等）", "避免久坐"],
             "priority": "high" if group in ("慢病", "重症") else "medium"},
            {"type": "sleep", "title": "睡眠处方",
             "content": ["保持每日7-8小时规律睡眠", "避免熬夜"],
             "priority": "medium"},
        ]
        if group in ("慢病", "重症"):
            prescriptions.append({
                "type": "monitoring", "title": "监测处方",
                "content": ["定期监测关键指标", "遵医嘱服药", "按时复查"],
                "priority": "high"
            })
        return prescriptions

    # ------------------------------------------------------------------
    # Main assess
    # ------------------------------------------------------------------

    def _build_risk_warnings(self, group: str, patient_data: dict) -> List[Dict[str, Any]]:
        """Build risk warnings based on group and indicators."""
        warnings = []
        sbp = patient_data.get('sbp') or patient_data.get('systolic_bp')
        if sbp:
            try:
                sv = float(sbp)
                if sv >= 180:
                    warnings.append({"title": "血压严重偏高", "description": f"收缩压{sbp}mmHg，需紧急就医", "level": "critical"})
                elif sv >= 140:
                    warnings.append({"title": "血压偏高", "description": f"收缩压{sbp}mmHg，建议规范治疗", "level": "medium"})
            except (ValueError, TypeError):
                pass
        bmi = patient_data.get('bmi')
        if bmi:
            try:
                bv = float(bmi)
                if bv >= 28:
                    warnings.append({"title": "肥胖预警", "description": f"BMI {bmi}，建议减重干预", "level": "high"})
                elif bv >= 24:
                    warnings.append({"title": "超重提醒", "description": f"BMI {bmi}，建议控制体重", "level": "low"})
            except (ValueError, TypeError):
                pass
        if group in ("慢病", "重症"):
            warnings.append({"title": "慢病风险提示", "description": f"当前分组为{group}，建议定期复查和规范管理", "level": "high" if group == "重症" else "medium"})
        return warnings

    def assess(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Main assessment function."""
        patient_data = self.extract_patient_data(input_data)

        # Validate required fields
        missing = []
        for field in ['age']:
            if patient_data.get(field) is None:
                missing.append(field)
        if missing:
            return {
                "success": False,
                "status": "incomplete",
                "message": "Missing required patient data",
                "required_fields": missing,
                "provided_data": patient_data,
            }

        # Derive BMI if we have height and weight
        if 'bmi' not in patient_data or patient_data.get('bmi') is None:
            h = patient_data.get('height')
            w = patient_data.get('weight')
            if h and w and float(h) > 0:
                patient_data['bmi'] = round(float(w) / ((float(h) / 100) ** 2), 1)

        # Score indicators and diseases
        ind_score, ind_basis, risk_indicators = self._score_indicators(patient_data)
        dis_score, dis_basis = self._score_diseases(patient_data)
        total_score = ind_score + dis_score
        all_basis = ind_basis + dis_basis

        # Determine groups (can be multiple)
        groups, follow_up = self._determine_groups(total_score)
        primary_group = groups[0]  # Highest-severity group

        # Build output
        modules = {
            "population_group": {
                "groups": groups,
                "primary_group": primary_group,
                "score": total_score,
                "basis": all_basis if all_basis else ["所有指标正常"],
                "risk_indicators": risk_indicators,
                "follow_up": follow_up,
            }
        }

        # Build per-group basis mapping
        group_classifications = []
        for g in groups:
            group_classifications.append({
                "category": g,
                "label": g,
            })

        # Health grouping basis - derive from diseases and indicators
        diseases = []
        disease_risks = []
        disease_staging = ""
        risk_grading = primary_group

        # From disease labels
        disease_labels = patient_data.get('disease_labels', [])
        if isinstance(disease_labels, list):
            disease_map = {
                "hypertension": "高血压", "diabetes": "糖尿病",
                "hyperlipidemia": "高血脂", "hyperuricemia": "高尿酸",
                "gout": "痛风", "copd": "慢性阻塞性肺疾病",
                "kidney_disease": "肾病", "liver_disease": "肝病",
                "cancer": "癌症", "heart_disease": "心脏病", "stroke": "中风",
            }
            for label in disease_labels:
                for key, zh_name in disease_map.items():
                    if key in str(label).lower():
                        diseases.append(zh_name)

        # From indicator thresholds
        sbp = patient_data.get('sbp')
        if sbp and float(sbp) >= 140:
            disease_risks.append("高血压")
            if not disease_staging:
                if float(sbp) >= 180: disease_staging = "3级高血压"
                elif float(sbp) >= 160: disease_staging = "2级高血压"
                else: disease_staging = "1级高血压"
        fg = patient_data.get('fasting_glucose')
        if fg and float(fg) >= 6.1:
            disease_risks.append("血糖异常")
            if not disease_staging:
                if float(fg) >= 7.0: disease_staging = "糖尿病"
                else: disease_staging = "糖尿病前期"
        tc = patient_data.get('tc')
        if tc and float(tc) >= 5.2:
            disease_risks.append("高胆固醇")
        bmi = patient_data.get('bmi')
        if bmi:
            bv = float(bmi)
            if bv >= 28: disease_risks.append("肥胖")
            elif bv >= 24: disease_risks.append("超重")
        if not diseases:
            diseases = ["暂无确诊疾病"]
        if not disease_risks:
            disease_risks = ["暂无明显风险"]

        structured_result = {
            "population_classification": {
                "primary_category": primary_group,
                "grouping_basis": [{
                    "disease": d if d != "暂无确诊疾病" else "",
                    "type": disease_staging if d != "暂无确诊疾病" else "",
                    "level": risk_grading or "",
                    "note": f"{disease_staging}{risk_grading or ''}" if d != "暂无确诊疾病" and disease_staging else (risk_grading or ""),
                } for d in (diseases if diseases and diseases != ["暂无确诊疾病"] else [primary_group])],
            },
            "recommended_data_collection": self._build_recommended_data(patient_data),
            "abnormal_indicators": self._build_abnormal_indicators(patient_data),
            "intervention_prescriptions": self._build_intervention_prescriptions(primary_group),
            "risk_warnings": self._build_risk_warnings(primary_group, patient_data),
        }

        return {
            "success": True,
            "status": "completed",
            "skill_name": "population-classification",
            "final_output": {
                "modules": modules,
                "total_modules": len(modules),
            },
            "structured_result": structured_result,
            "patient_data": {
                "age": patient_data.get('age'),
                "gender": patient_data.get('gender'),
            },
        }


def main():
    """CLI entry point."""
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='Population Classification')
    parser.add_argument('--input', help='Input file path (JSON) or natural text')
    parser.add_argument('--mode', default='standalone', choices=['standalone', 'skill'])

    args = parser.parse_args()
    classifier = PopulationClassifier()

    if args.mode == 'skill':
        input_data = None
        if args.input:
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError):
                pass

        if input_data is None:
            try:
                input_data = json.load(sys.stdin)
            except (json.JSONDecodeError, IOError):
                print(json.dumps({"success": False, "error": "Invalid JSON input"},
                                 ensure_ascii=False, indent=2))
                return 1

        result = classifier.assess(input_data)
        result["skill_name"] = "population-classification"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1

    if args.input:
        result = classifier.assess(args.input)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
