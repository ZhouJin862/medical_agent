"""Analyze session_0f36ea57d51b4f7d"""
import json

with open('data/memories/patient_001.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find all memories with session_0f36ea57d51b4f7d
session_memories = [m for m in data if m.get('metadata', {}).get('session_id') == 'session_0f36ea57d51b4f7d']

print(f"Session Analysis: session_0f36ea57d51b4f7d")
print("=" * 60)
print(f"Total messages: {len(session_memories)}")
print()

# Display each message with available metadata
for i, mem in enumerate(session_memories, 1):
    metadata = mem.get('metadata', {})
    memory = mem.get('memory', '')

    print(f"--- Message {i} ---")
    print(f"Role: {metadata.get('role', 'unknown')}")
    print(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
    print(f"Intent: {metadata.get('intent', 'N/A')}")

    # Check for skill-related fields
    if 'suggested_skill' in metadata:
        print(f"Suggested Skill: {metadata.get('suggested_skill')}")
    if 'confidence' in metadata:
        print(f"Confidence: {metadata.get('confidence')}")

    # Show content preview (first 100 chars) - skip unicode issues
    try:
        if len(memory) > 100:
            print(f"Content: {memory[:100]}...")
        else:
            print(f"Content: {memory}")
    except UnicodeEncodeError:
        print(f"Content: [Content contains special characters, length: {len(memory)}]")
    print()

# Summary
print("=" * 60)
print("Summary:")
print("-" * 60)

user_messages = [m for m in session_memories if m.get('metadata', {}).get('role') == 'user']
assistant_messages = [m for m in session_memories if m.get('metadata', {}).get('role') == 'assistant']

print(f"User messages: {len(user_messages)}")
print(f"Assistant messages: {len(assistant_messages)}")

# Collect intents used
intents_used = set()
for mem in session_memories:
    intent = mem.get('metadata', {}).get('intent')
    if intent:
        intents_used.add(intent)

print(f"Intents used: {intents_used if intents_used else 'None detected (general chat)'}")

# Check for skill routing
skills_used = []
for mem in session_memories:
    suggested_skill = mem.get('metadata', {}).get('suggested_skill')
    if suggested_skill:
        skills_used.append(suggested_skill)

if skills_used:
    print(f"Skills routed to: {skills_used}")
else:
    print("Skills routed to: None (LLM fallback/general_chat used)")
