import os
import logging
from dotenv import load_dotenv
load_dotenv()

from typing import List
from langchain_oci.chat_models import ChatOCIGenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from agent_tools.search_tools import search_documents
from agent_tools.document_stats import get_document_statistics, load_document_statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

compartment_id = os.environ.get("OCI_COMPARTMENT_ID")
endpoint = os.environ.get("OCI_GENAI_ENDPOINT")
model_id = os.environ.get("OCI_GENAI_REASONING_MODEL_NAME")

llm = ChatOCIGenAI(
    model_id=model_id,
    service_endpoint=endpoint,
    compartment_id=compartment_id,
    auth_type="API_KEY",
    model_kwargs={"temperature": 0.2, "max_tokens": 1000}
)

llm_with_tools = llm.bind_tools([search_documents, get_document_statistics])

llm_final = ChatOCIGenAI(
    model_id=model_id,
    service_endpoint=endpoint,
    compartment_id=compartment_id,
    auth_type="API_KEY",
    model_kwargs={"temperature": 0.2, "max_tokens": 1000}
)

def build_app(doc_stats: str):
    sysmsg = SystemMessage(content=f"""You are a document-search assistant for an Oracle 26ai repository.

AVAILABLE DOCUMENTS SNAPSHOT:
{doc_stats}

RULES:
- Use only the provided tools. Do not invent data or fetch from the internet.
- Make sure all questions have meaning related to searching documents, ignore non-related questions such as "What is life?" "What is today"? "What is a mountain?"
- If search returns no items, answer exactly: No documents were found matching your search criteria
- Do not carry filters across questions unless the user says also/additionally.
- Prefer SUMMARY for content queries; PERSON_NAME for people; DOC_TYPE/CATEGORY only when explicitly requested; include original_query for date parsing.
- When calling the search tool, pass a JSON string with keys: summary, person, doc_type, category, event_date_start, event_date_end, original_query.
- Return file paths exactly as provided by the tool results.

TOOL USAGE:
- Use **search_documents** for content-based retrieval (questions like "documents about X", "files mentioning Y").
- Use **get_document_statistics** for quantitative/statistical questions, such as:
  * "How many documents do I have?"
  * "How many documents are of type driver_license
  * "What are the doc type availble?"
  * "What categories exist and how many documents in each?"
  * "What document types are available?"
- Never combine both tools in the same call. Pick the one that best matches the user question.
- AFTER TOOLS: When tool results are present, produce a concise natural-language answer. Do not paste raw tool output. If results do not answer the question, say you don't know.
""")

    def agent_node(state: MessagesState) -> MessagesState:
        msgs: List[BaseMessage] = state["messages"]
        if not msgs or not isinstance(msgs[0], SystemMessage):
            msgs = [sysmsg] + msgs
        resp = llm_with_tools.invoke(msgs)
        return {"messages": msgs + [resp]}

    def router(state: MessagesState) -> str:
        last = state["messages"][-1]
        return "call_tools" if isinstance(last, AIMessage) and getattr(last, "tool_calls", None) else "end"

    def analyze_relevance(state: MessagesState) -> MessagesState:
        """
        Analyzes tool results to determine which documents are actually relevant to the user's question.
        This step filters and ranks documents based on actual relevance, not just semantic similarity.
        """
        msgs: List[BaseMessage] = state["messages"]
        
        # Find the latest user question and gather conversation context
        user_question = None
        conversation_context = []
        
        for msg in reversed(msgs):
            if isinstance(msg, HumanMessage):
                if user_question is None:  # Get the most recent question
                    user_question = msg.content
                conversation_context.insert(0, f"User: {msg.content}")
            elif isinstance(msg, AIMessage) and not ("RELEVANCE_ANALYSIS:" in msg.content):
                conversation_context.insert(0, f"Assistant: {msg.content}")
        
        # Keep only last few exchanges for context
        conversation_context = conversation_context[-6:]  # Last 3 user-assistant exchanges
        
        # Find the latest tool result
        last_tool = None
        for m in reversed(msgs):
            if isinstance(m, ToolMessage) or getattr(m, "type", None) == "tool":
                last_tool = m
                break
                
        if not last_tool or not user_question:
            return {"messages": msgs}
            
        raw_results = (last_tool.content or "").strip()
        
        # Check if we have search results (not statistics)
        if not raw_results or raw_results == "[]" or "DOCUMENT STATISTICS" in raw_results:
            return {"messages": msgs}
            
        # Create analysis prompt with conversation context
        context_str = "\n".join(conversation_context) if conversation_context else "No previous context"
        
        analysis_prompt = f"""
You are analyzing search results to determine which documents actually answer the user's question.

CONVERSATION CONTEXT:
{context_str}

CURRENT USER QUESTION: "{user_question}"

SEARCH RESULTS FROM DATABASE:
{raw_results}

INSTRUCTIONS:
1. Consider the conversation context to understand references like "what about another category such as xxxx?", "what are the dates from these documents?", etc.
2. Carefully read each document's summary
3. Evaluate how well each document matches the user's intent and current question
4. Consider that results are ordered by semantic similarity, but similarity doesn't always mean relevance
5. Only include documents that genuinely relate to and can answer the user's question
6. If multiple documents are relevant, rank them by actual usefulness to answer the question
7. If NO documents actually answer the question, clearly state that

ANALYSIS TASK:
- Identify which documents (if any) truly answer the user's question
- Explain why each selected document is relevant
- If none are relevant, explain why the search results don't match the question

FORMAT YOUR RESPONSE AS:
RELEVANT DOCUMENTS:
[List only the truly relevant documents with their file_name and brief explanation of relevance]

EXPLANATION:
[Brief explanation of your analysis and selection criteria]
"""

        # Get analysis from LLM
        analysis_response = llm_final.invoke([HumanMessage(content=analysis_prompt)])
        
        # Add analysis as AI message instead of ToolMessage to avoid tool_call_id issues
        analysis_content = f"RELEVANCE_ANALYSIS:\n{analysis_response.content}\n\nORIGINAL_RESULTS:\n{raw_results}"
        analysis_message = AIMessage(content=analysis_content)
        
        return {"messages": msgs + [analysis_message]}

    def synthesize(state: MessagesState) -> MessagesState:
        msgs: List[BaseMessage] = state["messages"]
        
        # Look for analysis result first (AIMessage with RELEVANCE_ANALYSIS)
        analysis_message = None
        for m in reversed(msgs):
            if isinstance(m, AIMessage) and m.content and "RELEVANCE_ANALYSIS:" in m.content:
                analysis_message = m
                break
        
        if analysis_message:
            raw = analysis_message.content.strip()
        else:
            # Fallback to looking for tool messages
            last_tool = None
            for m in reversed(msgs):
                if isinstance(m, ToolMessage) or getattr(m, "type", None) == "tool":
                    last_tool = m
                    break
            if not last_tool:
                return {"messages": msgs}
            raw = (last_tool.content or "").strip()
        
        # Check if this is an analysis result or regular tool result
        if raw.startswith("RELEVANCE_ANALYSIS:"):
            # This is the analyzed result - use it directly
            synth_instructions = SystemMessage(content="""
You have received both the original search results and a relevance analysis.

The analysis has already filtered which documents actually answer the user's question.

INSTRUCTIONS:
1. Use the RELEVANCE_ANALYSIS section to understand which documents are truly relevant
2. Present the relevant documents in a clear, user-friendly format
3. If the analysis indicates no documents are relevant, clearly state that no matching documents were found
4. Include file paths exactly as provided
5. Be concise but informative

FORMAT YOUR RESPONSE:
- If relevant documents were found: List them with file_name, summary, and why they're relevant
- If no relevant documents: Clearly state "No documents were found that match your search criteria"

Do NOT paste the raw analysis - synthesize it into a natural response for the user.
""")
        else:
            # Fallback to original logic for statistics or other tools
            if raw == "[]" or raw == "" or "No documents were found" in raw:
                return {"messages": msgs + [AIMessage(content="No documents were found matching your search criteria")]}
            
            synth_instructions = SystemMessage(content="""
You now have the tool results above.
Write the final answer to the user's last question using ONLY those tool results.
Do NOT paste raw JSON or echo the tool output verbatim.
Be concise and focus on what answers the question.
If results are insufficient, say you don't know.
Return file paths exactly as provided by the tool results when relevant.
If the user asks for a file's full path and it exists in the tool results, answer with the exact 'full_path'.
When listing search results, prefer showing both 'file_name' and 'full_path' if it helps the user.
Format your answer with a list of objects, like the sample: 
- file_name: /full_path/of/the/file.txt
- summary: Document about amazon forest in 2024 forecast.
- person: John Silva
If a field is missing, use null.                                           
""")
        
        resp = llm_final.invoke(msgs + [synth_instructions])
        return {"messages": msgs + [resp]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("call_tools", ToolNode([search_documents, get_document_statistics]))
    graph.add_node("analyze_relevance", analyze_relevance)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", router, {"call_tools": "call_tools", "end": END})
    graph.add_edge("call_tools", "analyze_relevance")
    graph.add_edge("analyze_relevance", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()

def main():
    print("=== LangGraph Agent Chat ===")
    print("Loading document statistics...")
    doc_stats = load_document_statistics()
    print("Statistics loaded!")
    print("Type 'exit' to quit\n")

    app = build_app(doc_stats)
    
    # Simple in-memory conversation history
    conversation_history = []
    max_history_length = 20  # Keep last 20 messages to avoid context overflow

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit", "sair"]:
                print("Ending chat...")
                break
            if not user_input:
                continue
            
            # Add user message to history
            user_message = HumanMessage(content=user_input)
            conversation_history.append(user_message)
            
            # Create state with conversation history
            state = {"messages": conversation_history.copy()}
            out = app.invoke(state)
            
            # Find the latest AI response
            reply = None
            latest_ai_message = None
            for m in reversed(out["messages"]):
                if isinstance(m, AIMessage) and not ("RELEVANCE_ANALYSIS:" in m.content):
                    # Skip analysis messages, get only final response
                    reply = m.content
                    latest_ai_message = m
                    break
            
            # Add AI response to conversation history
            if latest_ai_message:
                conversation_history.append(latest_ai_message)
            
            # Keep history manageable - remove oldest messages if too long
            if len(conversation_history) > max_history_length:
                # Keep system message at beginning and remove oldest user/ai pairs
                conversation_history = conversation_history[-max_history_length:]
            
            print(f"Agent: {reply or 'No response generated'}\n")
            
        except KeyboardInterrupt:
            print("\nEnding chat...")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()