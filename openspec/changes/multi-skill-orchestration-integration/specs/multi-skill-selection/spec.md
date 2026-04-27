# Multi-Skill Selection Specification

## ADDED Requirements

### Requirement: Multi-intent detection

The system SHALL detect multiple distinct intents within a single user input and identify all relevant skills needed to address those intents.

#### Scenario: User requests two independent assessments

- **WHEN** user input contains "check my blood pressure and diabetes risk"
- **THEN** system SHALL detect two distinct intents: blood pressure assessment AND diabetes assessment
- **THEN** system SHALL select both `hypertension-assessment` AND `diabetes-assessment` skills

#### Scenario: User requests three related assessments

- **WHEN** user input contains "evaluate my heart health including cholesterol"
- **THEN** system SHALL detect multiple related intents
- **THEN** system SHALL select relevant skills including cardiovascular risk assessment

### Requirement: Skill relationship analysis

The system SHALL analyze relationships between selected skills to determine execution strategy (independent, sequential, or complementary).

#### Scenario: Independent skills detected

- **WHEN** selected skills assess independent domains (e.g., blood pressure AND diabetes)
- **THEN** system SHALL mark relationship as "independent"
- **THEN** system SHALL suggest parallel execution

#### Scenario: Sequential skills detected

- **WHEN** one skill's output informs another skill (e.g., assessment → prescription)
- **THEN** system SHALL mark relationship as "sequential"
- **THEN** system SHALL suggest sequential execution with context passing

#### Scenario: Complementary skills detected

- **WHEN** skills enhance each other (e.g., assessment + dietary advice)
- **THEN** system SHALL mark relationship as "complementary"
- **THEN** system SHALL suggest enhance aggregation strategy

### Requirement: Fallback to single skill

The system SHALL gracefully fall back to single-skill mode when multi-skill detection fails or is unnecessary.

#### Scenario: Single intent detected

- **WHEN** user input contains only one clear intent
- **THEN** system SHALL select exactly one primary skill
- **THEN** system SHALL NOT attempt multi-skill execution

#### Scenario: Multi-skill selection fails

- **WHEN** LLM multi-skill selection returns invalid or unparseable response
- **THEN** system SHALL fall back to keyword-based single-skill selection
- **THEN** system SHALL log the failure for debugging

### Requirement: Alternative skills identification

The system SHALL identify alternative skills as backup options when primary skill selection has low confidence.

#### Scenario: Low confidence primary skill

- **WHEN** primary skill confidence is below 0.7
- **THEN** system SHALL include alternative skills in selection result
- **THEN** system SHALL rank alternatives by confidence score

#### Scenario: No clear skill match

- **WHEN** no skill achieves minimum confidence threshold
- **THEN** system SHALL return empty primary selection
- **THEN** system SHALL include all potential skills as alternatives
