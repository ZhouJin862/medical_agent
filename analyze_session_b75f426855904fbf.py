"""Analyze session_b75f426855904fbf"""
import json

with open('data/memories/patient_001.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find all memories with session_b75f426855904fbf
session_memories = [m for m in data if m.get('metadata', {}).get('session_id') == 'session_b75f426855904fbf']

output = []
output.append("=" * 70)
output.append("Session Analysis: session_b75f426855904fbf")
output.append("=" * 70)
output.append(f"Total messages: {len(session_memories)}")
output.append("")

# Display each message
for i, mem in enumerate(session_memories, 1):
    metadata = mem.get('metadata', {})
    memory = mem.get('memory', '')

    output.append(f"--- Message {i} ({metadata.get('role')}) ---")

    # Check for skill metadata
    intent = metadata.get('intent')
    suggested_skill = metadata.get('suggested_skill')
    confidence = metadata.get('confidence')

    if intent:
        output.append(f"  Intent: {intent}")
    if suggested_skill:
        output.append(f"  Suggested Skill: {suggested_skill}")
    if confidence is not None:
        output.append(f"  Confidence: {confidence}")

    # Show content (truncated to avoid encoding issues)
    content_preview = memory[:150].replace('\n', ' ') + "..." if len(memory) > 150 else memory.replace('\n', ' ')
    output.append(f"  Content: {content_preview}")
    output.append("")

# Summary
output.append("=" * 70)
output.append("Summary:")
output.append("=" * 70)

skills_used = set()
intents_used = set()
executed_skills_info = []

for mem in session_memories:
    metadata = mem.get('metadata', {})
    if metadata.get('suggested_skill'):
        skills_used.add(metadata.get('suggested_skill'))
    if metadata.get('intent'):
        intents_used.add(metadata.get('intent'))
    if metadata.get('executed_skills'):
        executed_skills_info.extend(metadata.get('executed_skills'))

if skills_used:
    output.append(f"Skills Matched: {skills_used}")
else:
    output.append("Skills Matched: None (no skill metadata - old session)")

if intents_used:
    output.append(f"Intents: {intents_used}")
else:
    output.append("Intents: None (no intent metadata - old session)")

if executed_skills_info:
    output.append(f"Skills Executed: {len(executed_skills_info)} executions")
    for skill_info in executed_skills_info:
        output.append(f"  - {skill_info.get('skill_name')}: success={skill_info.get('success')}")

# Save to file
with open('session_b75f426855904fbf_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('Analysis saved to session_b75f426855904fbf_analysis.txt')

# Print to console with ASCII-only output
print('\n' + '=' * 70)
print('Session Analysis: session_b75f426855904fbf')
print('=' * 70)
print(f'Total messages: {len(session_memories)}')
print()

for i, mem in enumerate(session_memories, 1):
    metadata = mem.get('metadata', {})
    role = metadata.get('role', 'unknown')

    print(f'Message {i}: {role}')

    intent = metadata.get('intent')
    suggested_skill = metadata.get('suggested_skill')
    confidence = metadata.get('confidence')

    if intent or suggested_skill or confidence is not None:
        if intent:
            print(f'  Intent: {intent}')
        if suggested_skill:
            print(f'  Skill: {suggested_skill}')
        if confidence is not None:
            print(f'  Confidence: {confidence}')
    else:
        print('  (No skill metadata - old session)')

print()
print('Summary:')
if skills_used:
    print(f'  Skills: {skills_used}')
else:
    print('  Skills: None (old session without skill tracking)')
