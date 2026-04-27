"""
Integration tests for LangGraph workflow.

This test module covers the end-to-end workflow execution including:
- load_patient node (calls MCP ProfileMCPClient)
- retrieve_memory node (calls Mem0)
- classify_intent node (supports @skill_name syntax)
- route_skill node (conditional routing based on intent)
- aggregate_results node
- save_memory node
"""
