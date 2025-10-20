"""
Specialized Agent Cards for A2A Protocol

This module defines agent cards for the specialized Chain of Thought agents:
- Planner Agent: Strategic planning and problem decomposition
- Researcher Agent: Information gathering and analysis
- Reasoner Agent: Logical reasoning and conclusion drawing
- Synthesizer Agent: Information synthesis and response generation

Each agent can be deployed independently and communicate via A2A protocol.
"""

from a2a_models import AgentCard, AgentCapability, AgentEndpoint
from typing import Dict


def get_planner_agent_card(base_url: str = "http://localhost:8000") -> dict:
    """Get the agent card for the Planner agent"""
    
    capabilities = [
        AgentCapability(
            name="agent.query",
            description="Break down complex problems into 3-4 clear, manageable steps for systematic problem solving",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query or problem to break down"
                    },
                    "context": {
                        "type": "array",
                        "description": "Optional context from previous processing",
                        "items": {"type": "object"}
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of planned steps"
                    },
                    "plan": {
                        "type": "string",
                        "description": "Detailed plan for addressing the query"
                    }
                }
            }
        )
    ]
    
    endpoint = AgentEndpoint(
        base_url=base_url,
        authentication={
            "type": "bearer_token",
            "required": False,
            "description": "Optional bearer token authentication"
        }
    )
    
    agent_card = AgentCard(
        agent_id="planner_agent_v1",
        name="Strategic Planner Agent",
        version="1.0.0",
        description="Specialized agent for strategic planning and problem decomposition. Breaks down complex queries into clear, actionable steps for systematic problem-solving.",
        capabilities=capabilities,
        endpoints=endpoint,
        metadata={
            "personality": "analytical, strategic, methodical",
            "role": "Strategic Planner",
            "expertise": ["problem_decomposition", "strategic_planning", "task_breakdown"],
            "reasoning_style": "top-down, structured",
            "specialization": "query_planning",
            "agent_type": "cot_specialized",
            "max_steps": 4,
            "deployment_type": "microservice"
        }
    )
    
    return agent_card.model_dump()


def get_researcher_agent_card(base_url: str = "http://localhost:8000") -> dict:
    """Get the agent card for the Researcher agent"""
    
    capabilities = [
        AgentCapability(
            name="agent.query",
            description="Gather and analyze relevant information from knowledge bases, extracting key findings for each research step",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The original query being researched"
                    },
                    "step": {
                        "type": "string",
                        "description": "The specific step to research"
                    },
                    "context": {
                        "type": "array",
                        "description": "Context from previous processing",
                        "items": {"type": "object"}
                    }
                },
                "required": ["query", "step"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Research findings with context"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of key research findings"
                    }
                }
            }
        )
    ]
    
    endpoint = AgentEndpoint(
        base_url=base_url,
        authentication={
            "type": "bearer_token",
            "required": False,
            "description": "Optional bearer token authentication"
        }
    )
    
    agent_card = AgentCard(
        agent_id="researcher_agent_v1",
        name="Information Researcher Agent",
        version="1.0.0",
        description="Specialized agent for information gathering and analysis. Searches knowledge bases, extracts relevant information, and summarizes key findings for each research step.",
        capabilities=capabilities,
        endpoints=endpoint,
        metadata={
            "personality": "curious, thorough, detail-oriented",
            "role": "Information Gatherer",
            "expertise": ["information_retrieval", "knowledge_extraction", "data_analysis"],
            "reasoning_style": "bottom-up, evidence-based",
            "specialization": "research",
            "agent_type": "cot_specialized",
            "requires_vector_store": True,
            "deployment_type": "microservice"
        }
    )
    
    return agent_card.model_dump()


def get_reasoner_agent_card(base_url: str = "http://localhost:8000") -> dict:
    """Get the agent card for the Reasoner agent"""
    
    capabilities = [
        AgentCapability(
            name="agent.query",
            description="Apply logical reasoning and analysis to information, drawing clear conclusions for each step",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The original query being reasoned about"
                    },
                    "step": {
                        "type": "string",
                        "description": "The specific step to reason about"
                    },
                    "context": {
                        "type": "array",
                        "description": "Research findings and context for reasoning",
                        "items": {"type": "object"}
                    }
                },
                "required": ["query", "step", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "conclusion": {
                        "type": "string",
                        "description": "Logical conclusion for this step"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Detailed reasoning process"
                    }
                }
            }
        )
    ]
    
    endpoint = AgentEndpoint(
        base_url=base_url,
        authentication={
            "type": "bearer_token",
            "required": False,
            "description": "Optional bearer token authentication"
        }
    )
    
    agent_card = AgentCard(
        agent_id="reasoner_agent_v1",
        name="Logic and Reasoning Agent",
        version="1.0.0",
        description="Specialized agent for logical reasoning and analysis. Applies critical thinking to information, identifies patterns, and draws well-reasoned conclusions.",
        capabilities=capabilities,
        endpoints=endpoint,
        metadata={
            "personality": "logical, critical, analytical",
            "role": "Logic and Analysis",
            "expertise": ["logical_reasoning", "critical_thinking", "pattern_recognition"],
            "reasoning_style": "deductive, inductive, abductive",
            "specialization": "reasoning",
            "agent_type": "cot_specialized",
            "deployment_type": "microservice"
        }
    )
    
    return agent_card.model_dump()


def get_synthesizer_agent_card(base_url: str = "http://localhost:8000") -> dict:
    """Get the agent card for the Synthesizer agent"""
    
    capabilities = [
        AgentCapability(
            name="agent.query",
            description="Combine multiple reasoning steps into a clear, comprehensive final answer",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The original query"
                    },
                    "reasoning_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "All reasoning steps to synthesize"
                    },
                    "context": {
                        "type": "array",
                        "description": "Additional context for synthesis",
                        "items": {"type": "object"}
                    }
                },
                "required": ["query", "reasoning_steps"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Synthesized final answer"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of the synthesis process"
                    }
                }
            }
        )
    ]
    
    endpoint = AgentEndpoint(
        base_url=base_url,
        authentication={
            "type": "bearer_token",
            "required": False,
            "description": "Optional bearer token authentication"
        }
    )
    
    agent_card = AgentCard(
        agent_id="synthesizer_agent_v1",
        name="Information Synthesis Agent",
        version="1.0.0",
        description="Specialized agent for information synthesis and response generation. Combines multiple reasoning steps into coherent, comprehensive final answers.",
        capabilities=capabilities,
        endpoints=endpoint,
        metadata={
            "personality": "integrative, clear, comprehensive",
            "role": "Information Synthesizer",
            "expertise": ["information_synthesis", "summarization", "coherent_writing"],
            "reasoning_style": "holistic, integrative",
            "specialization": "synthesis",
            "agent_type": "cot_specialized",
            "deployment_type": "microservice"
        }
    )
    
    return agent_card.model_dump()


def get_all_specialized_agent_cards(config: Dict[str, str] = None) -> Dict[str, dict]:
    """Get all specialized agent cards with their configured URLs"""
    
    if config is None:
        config = {
            "planner_url": "http://localhost:8000",
            "researcher_url": "http://localhost:8000",
            "reasoner_url": "http://localhost:8000",
            "synthesizer_url": "http://localhost:8000"
        }
    
    return {
        "planner_agent_v1": get_planner_agent_card(config.get("planner_url", "http://localhost:8000")),
        "researcher_agent_v1": get_researcher_agent_card(config.get("researcher_url", "http://localhost:8000")),
        "reasoner_agent_v1": get_reasoner_agent_card(config.get("reasoner_url", "http://localhost:8000")),
        "synthesizer_agent_v1": get_synthesizer_agent_card(config.get("synthesizer_url", "http://localhost:8000"))
    }


def get_agent_card_by_id(agent_id: str, config: Dict[str, str] = None) -> dict:
    """Get a specific agent card by agent ID"""
    all_cards = get_all_specialized_agent_cards(config)
    return all_cards.get(agent_id, None)

