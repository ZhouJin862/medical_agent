# Skill Orchestration Specification

## ADDED Requirements

### Requirement: Execution plan creation

The system SHALL create an execution plan from multi-skill selection that defines skills, execution mode, and aggregation strategy.

#### Scenario: Parallel execution plan for independent skills

- **WHEN** selected skills have independent relationships
- **THEN** system SHALL create execution plan with execution_mode="parallel"
- **THEN** system SHALL include all selected skills in a single execution group
- **THEN** system SHALL set aggregation_strategy="merge"

#### Scenario: Sequential execution plan for dependent skills

- **WHEN** selected skills have sequential relationships
- **THEN** system SHALL create execution plan with execution_mode="sequential"
- **THEN** system SHALL create separate execution groups for each skill in dependency order
- **THEN** system SHALL set aggregation_strategy="chain"

#### Scenario: Mixed execution plan

- **WHEN** selected skills have both independent and sequential relationships
- **THEN** system SHALL create execution plan with execution_mode="mixed"
- **THEN** system SHALL group independent skills together for parallel execution
- **THEN** system SHALL order sequential groups based on dependencies

### Requirement: Parallel skill execution

The system SHALL execute independent skills concurrently using asyncio.gather().

#### Scenario: Two skills execute in parallel

- **WHEN** execution plan specifies parallel mode with 2 skills
- **THEN** system SHALL execute both skills concurrently
- **THEN** system SHALL complete execution when both skills finish (whichever is slower)
- **THEN** total execution time SHALL be approximately max(individual times), not sum

#### Scenario: One parallel skill fails

- **WHEN** one skill in parallel execution fails
- **THEN** system SHALL continue executing other skills to completion
- **THEN** system SHALL include error from failed skill in final result
- **THEN** system SHALL mark overall result as partial success

### Requirement: Sequential skill execution with context passing

The system SHALL execute dependent skills in order, passing results from each skill as context to the next.

#### Scenario: Two skills execute sequentially

- **WHEN** execution plan specifies sequential mode with 2 skills
- **THEN** system SHALL execute first skill to completion
- **THEN** system SHALL pass first skill's output as context to second skill
- **THEN** system SHALL execute second skill with enhanced context

#### Scenario: Sequential skill context includes structured data

- **WHEN** a skill produces structured_output (dict)
- **THEN** system SHALL merge this data into patient_context for next skill
- **THEN** next skill SHALL have access to previous skill's structured data

### Requirement: Mixed execution mode

The system SHALL support mixed execution where some groups run in parallel and others run sequentially.

#### Scenario: Mixed plan with parallel first, then sequential

- **WHEN** execution plan has mixed mode with independent group followed by sequential group
- **THEN** system SHALL execute independent skills in parallel first
- **THEN** system SHALL aggregate parallel results
- **THEN** system SHALL pass aggregated results as context to sequential skills
- **THEN** system SHALL execute sequential skills in order

### Requirement: Skill execution timeout

The system SHALL enforce a maximum timeout for each skill execution.

#### Scenario: Skill exceeds timeout

- **WHEN** a skill execution exceeds 30 seconds
- **THEN** system SHALL cancel the skill execution
- **THEN** system SHALL return error result with "timeout" message
- **THEN** system SHALL continue with other skills in parallel/sequential execution

### Requirement: Execution result tracking

The system SHALL track execution time, success/failure, and output for each skill.

#### Scenario: Successful skill execution

- **WHEN** a skill executes successfully
- **THEN** system SHALL record skill_name, success=True, execution_time_ms, and response
- **THEN** system SHALL include structured_output if skill produces structured data

#### Scenario: Failed skill execution

- **WHEN** a skill execution raises exception
- **THEN** system SHALL record skill_name, success=False, execution_time_ms, and error message
- **THEN** system SHALL NOT include response or structured_output
