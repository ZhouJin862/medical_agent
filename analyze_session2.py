"""Analyze session_0f36ea57d51b4f7d and save to file"""
import json

with open('data/memories/patient_001.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find all memories with session_0f36ea57d51b4f7d
session_memories = [m for m in data if m.get('metadata', {}).get('session_id') == 'session_0f36ea57d51b4f7d']

output = []
output.append("Session Analysis: session_0f36ea57d51b4f7d")
output.append("=" * 60)
output.append(f"Total messages: {len(session_memories)}")
output.append("")

# Display each message with available metadata
for i, mem in enumerate(session_memories, 1):
    metadata = mem.get('metadata', {})
    memory = mem.get('memory', '')

    output.append(f"--- Message {i} ---")
    output.append(f"Role: {metadata.get('role', 'unknown')}")
    output.append(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
    output.append(f"Intent: {metadata.get('intent', 'N/A')}")

    # Check for skill-related fields
    if 'suggested_skill' in metadata:
        output.append(f"Suggested Skill: {metadata.get('suggested_skill')}")
    if 'confidence' in metadata:
        output.append(f"Confidence: {metadata.get('confidence')}")

    # Show content preview
    content_preview = memory[:100] + "..." if len(memory) > 100 else memory
    output.append(f"Content: {content_preview}")
    output.append("")

# Summary
output.append("=" * 60)
output.append("Summary:")
output.append("-" * 60)

user_messages = [m for m in session_memories if m.get('metadata', {}).get('role') == 'user']
assistant_messages = [m for m in session_memories if m.get('metadata', {}).get('role') == 'assistant']

output.append(f"User messages: {len(user_messages)}")
output.append(f"Assistant messages: {len(assistant_messages)}")

# Collect intents used
intents_used = set()
for mem in session_memories:
    intent = mem.get('metadata', {}).get('intent')
    if intent:
        intents_used.add(intent)

output.append(f"Intents used: {intents_used if intents_used else 'None detected (general chat)'}")

# Check for skill routing
skills_used = []
for mem in session_memories:
    suggested_skill = mem.get('metadata', {}).get('suggested_skill')
    if suggested_skill:
        skills_used.append(suggested_skill)

if skills_used:
    output.append(f"Skills routed to: {skills_used}")
else:
    output.append("Skills routed to: None (LLM fallback/general_chat used)")

# Save to file
with open('session_analysis_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Analysis saved to session_analysis_result.txt")
