# Result Aggregation Specification

## ADDED Requirements

### Requirement: Merge aggregation for independent skills

The system SHALL merge results from independent skills into a cohesive multi-part response.

#### Scenario: Merge two independent assessment results

- **WHEN** two independent skills complete successfully
- **THEN** system SHALL create response with "Based on my analysis:" header
- **THEN** system SHALL include each skill's response with formatted skill name as heading
- **THEN** system SHALL present results in logical order

#### Scenario: Merge with one failed skill

- **WHEN** one skill fails and one succeeds in parallel execution
- **THEN** system SHALL include successful skill's result
- **THEN** system SHALL note that one skill encountered issues
- **THEN** system SHALL NOT include error details in user-facing response

#### Scenario: Merge structured outputs

- **WHEN** multiple skills produce structured_output dictionaries
- **THEN** system SHALL merge all structured outputs into single dictionary
- **THEN** system SHALL merge top-level keys (later skills overwrite earlier on conflict)
- **THEN** system SHALL merge nested dictionaries recursively
- **THEN** system SHALL extend lists when same key contains list

### Requirement: Chain aggregation for sequential skills

The system SHALL chain results from sequential skills, using the final skill's output as the primary response.

#### Scenario: Chain two sequential skill results

- **WHEN** two skills execute sequentially
- **THEN** system SHALL use the last (final) skill's response as the aggregated response
- **THEN** system SHALL discard intermediate skill responses from user-facing output
- **THEN** system SHALL preserve structured output from final skill only

#### Scenario: Chain with failure in middle

- **WHEN** a middle skill in sequential chain fails
- **THEN** system SHALL stop sequential execution
- **THEN** system SHALL use last successful result as aggregated response
- **THEN** system SHALL include error information in metadata

### Requirement: Enhance aggregation for complementary skills

The system SHALL enhance primary result with insights from complementary skills.

#### Scenario: Enhance with one complementary skill

- **WHEN** primary skill and one complementary skill complete
- **THEN** system SHALL use primary skill's response as base
- **THEN** system SHALL append "## Additional Insights" section
- **THEN** system SHALL include complementary skill's name and truncated summary (max 200 chars)

#### Scenario: Enhance with multiple complementary skills

- **WHEN** primary skill and multiple complementary skills complete
- **THEN** system SHALL list all complementary skills under "Additional Insights"
- **THEN** each complementary skill SHALL have name and brief summary
- **THEN** primary skill's full response SHALL remain intact

### Requirement: Aggregated structured output

The system SHALL produce structured output that combines results according to the aggregation strategy.

#### Scenario: Structured merge output

- **WHEN** aggregation strategy is "merge"
- **THEN** system SHALL produce structured_output with all skills' data combined
- **THEN** conflicting keys SHALL be resolved by last-write-wins

#### Scenario: Structured chain output

- **WHEN** aggregation strategy is "chain"
- **THEN** system SHALL produce structured_output from final skill only
- **THEN** intermediate skills' structured outputs SHALL be discarded

#### Scenario: Structured enhance output

- **WHEN** aggregation strategy is "enhance"
- **THEN** system SHALL produce structured_output with primary skill's data
- **THEN** system SHALL add "complementary_results" key containing all skills' structured outputs

### Requirement: Error handling in aggregation

The system SHALL handle various error scenarios during result aggregation.

#### Scenario: All skills failed

- **WHEN** all executed skills fail
- **THEN** system SHALL return generic apology message
- **THEN** system SHALL NOT include any skill-specific content
- **THEN** system SHALL set success=False on MultiSkillExecutionResult

#### Scenario: No successful results to aggregate

- **WHEN** no skill produced a valid response
- **THEN** system SHALL return "I apologize, but I encountered issues processing your request"
- **THEN** system SHALL log detailed error information

### Requirement: Response formatting

The system SHALL format aggregated responses in a readable, professional manner.

#### Scenario: Skill name formatting

- **WHEN** including skill names in aggregated response
- **THEN** system SHALL convert kebab-case to Title Case (e.g., "hypertension-assessment" → "Hypertension Assessment")
- **THEN** skill names SHALL be rendered as bold markdown headings

#### Scenario: Section separation

- **WHEN** aggregating multiple skill results
- **THEN** system SHALL separate each skill's result with blank lines
- **THEN** system SHALL use consistent heading levels throughout
