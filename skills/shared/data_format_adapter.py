"""Shared adapter to convert API format to skill-expected nested format.

API sends: {patient_data: {age, gender}, vital_signs: {systolic_bp, ...}, medical_history: {...}}
Validator expects: {patient_info: {age, gender}, health_metrics: {blood_pressure: {systolic, ...}, ...}}

Validator health_metrics structure:
  blood_pressure: {systolic, diastolic}    (nested dict)
  blood_glucose:  {fasting, hba1c}         (nested dict, key is 'fasting' not 'fasting_glucose')
  blood_lipid:    {tc, tg, ldl_c, hdl_c}   (nested dict)
  uric_acid:      <float>                  (DIRECT key, not nested under kidney)
  bmi:            <float or dict>           (DIRECT key, not nested under basic)
"""
from typing import Any, Dict, Optional

# Nested field mapping: API field → (category_dict, internal_key)
_NESTED_MAP = {
    'systolic_bp': ('blood_pressure', 'systolic'),
    'diastolic_bp': ('blood_pressure', 'diastolic'),
    'total_cholesterol': ('blood_lipid', 'tc'),
    'tc': ('blood_lipid', 'tc'),
    'tg': ('blood_lipid', 'tg'),
    'ldl_c': ('blood_lipid', 'ldl_c'),
    'hdl_c': ('blood_lipid', 'hdl_c'),
    'fasting_glucose': ('blood_glucose', 'fasting'),
    'hba1c': ('blood_glucose', 'hba1c'),
    'height': ('basic', 'height'),
    'weight': ('basic', 'weight'),
    'waist': ('basic', 'waist_circumference'),
    'waist_circumference': ('basic', 'waist_circumference'),
}

# Direct field mapping: API field → health_metrics top-level key
_DIRECT_MAP = {
    'uric_acid': 'uric_acid',
}


def adapt_agent_format(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert {patient_data, vital_signs} to {patient_info, health_metrics}."""
    if 'patient_info' in input_data or 'health_metrics' in input_data:
        return input_data  # already in expected format

    result = dict(input_data)

    # Build patient_info from patient_data
    patient_info = {}
    if 'patient_data' in input_data:
        pd = input_data['patient_data']
        if isinstance(pd, dict):
            if 'basic_info' in pd:  # nested agent format
                bi = pd['basic_info']
                patient_info['age'] = _to_int(bi.get('age'))
                patient_info['gender'] = bi.get('gender', 'male')
            else:  # flat format
                patient_info['age'] = _to_int(pd.get('age'))
                patient_info['gender'] = pd.get('gender', 'male')
    if patient_info:
        result['patient_info'] = patient_info

    # Build health_metrics from vital_signs
    health_metrics = {
        'basic': {}, 'blood_pressure': {},
        'blood_glucose': {}, 'blood_lipid': {},
    }
    bmi_dict = {}  # Collect bmi, height, weight, waist for the bmi field

    if 'vital_signs' in input_data:
        vs = input_data['vital_signs']
        if isinstance(vs, dict):
            for api_field, value in vs.items():
                if value is None:
                    continue
                if api_field in _NESTED_MAP:
                    cat, name = _NESTED_MAP[api_field]
                    # Normalize units: height/waist in cm → m (validator expects meters)
                    if name in ('height', 'waist_circumference'):
                        value = _cm_to_m(value)
                    health_metrics[cat][name] = value
                    # Also collect for bmi dict
                    if name == 'height':
                        bmi_dict['height'] = value
                    elif name == 'weight':
                        bmi_dict['weight'] = value
                    elif name == 'waist_circumference':
                        bmi_dict['waist_circumference'] = value
                elif api_field == 'bmi':
                    bmi_dict['value'] = value
                elif api_field in _DIRECT_MAP:
                    health_metrics[_DIRECT_MAP[api_field]] = value

    # Build bmi as a dict with value + height/weight/waist (risk_calculator needs these)
    if bmi_dict:
        if 'value' not in bmi_dict and 'height' in bmi_dict and 'weight' in bmi_dict:
            h = bmi_dict['height']
            if h and h > 0:
                bmi_dict['value'] = round(bmi_dict['weight'] / (h * h), 2)
        health_metrics['bmi'] = bmi_dict

    result['health_metrics'] = health_metrics

    return result


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return value


def _cm_to_m(value) -> float:
    """Convert cm to meters if value > 2.5 (already in meters if <= 2.5)."""
    try:
        v = float(value)
        return v / 100.0 if v > 2.5 else v
    except (TypeError, ValueError):
        return value
