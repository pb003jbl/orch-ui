import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Joint Integration Design Smart Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# Custom CSS
# ============================================================================

st.markdown("""
<style>
    /* Main theme */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --success-color: #10b981;
        --error-color: #ef4444;
        --warning-color: #f59e0b;
    }

    .json-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border-radius: 6px;
        padding: 12px;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 12px;
        overflow-x: auto;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:9000")

# ============================================================================
# Session State
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"thread_{int(time.time())}"

if "task_plans" not in st.session_state:
    st.session_state.task_plans = []

if "execution_history" not in st.session_state:
    st.session_state.execution_history = []

# ============================================================================
# Helper Functions
# ============================================================================

def call_orchestrator(query: str, thread_id: str) -> Optional[Dict[str, Any]]:
    """Call orchestrator API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/orchestrate",
            json={"query": query, "thread_id": thread_id},
            timeout=120
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to orchestrator at {API_BASE_URL}")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def display_task_plan(plan: Dict[str, Any]):
    """Display task plan - NO NESTED EXPANDERS"""
    if not plan:
        return

    # Use columns instead of nested content
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Agents", len(plan.get("agents", [])))

    with col2:
        confidence = plan.get("confidence", 0)
        st.metric("Confidence", f"{int(confidence * 100)}%")

    with col3:
        uncertain = "Uncertain" if plan.get("uncertain", False) else "Confident"
        st.metric("Status", uncertain)

    st.write("**Reasoning:**")
    st.write(plan.get("reasoning", "N/A"))

    st.write("**Execution Order:**")
    for i, agent in enumerate(plan.get("agents", []), 1):
        st.write(f"  {i}. {agent}")


def display_agent_result(agent_name: str, result: Dict[str, Any]):
    """Display single agent result - NO NESTED EXPANDERS"""

    st.subheader(f"Agent: {agent_name}")

    # Status
    if result.get("error"):
        st.error(f"Error: {result['error']}")
    else:
        st.success("Success")

    # Response
    if result.get("response"):
        response = result["response"]

        st.write("**Response:**")

        # Try to display nicely
        if isinstance(response, str):
            try:
                # Try parsing as JSON for pretty display
                json_data = json.loads(response)
                st.json(json_data)
            except:
                # If not JSON, show as markdown
                st.markdown(response)
        else:
            st.json(response)

    # Metadata
    if result.get("metadata"):
        st.write("**Metadata:**")
        st.json(result["metadata"])

    st.divider()


# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.title("Configuration")

    # API URL
    api_url = st.text_input(
        "Orchestrator URL",
        value=API_BASE_URL,
        help="URL of the orchestrator API"
    )
    if api_url != API_BASE_URL:
        API_BASE_URL = api_url

    st.divider()

    # Thread Management
    st.subheader("Thread Management")
    st.write(f"**Thread ID:**")
    st.code(st.session_state.thread_id, language=None)

    if st.button("New Thread", use_container_width=True):
        st.session_state.thread_id = f"thread_{int(time.time())}"
        st.session_state.messages = []
        st.session_state.task_plans = []
        st.session_state.execution_history = []
        st.rerun()

    st.divider()

    # Statistics
    st.subheader("Statistics")
    st.metric("Messages", len(st.session_state.messages))
    st.metric("Task Plans", len(st.session_state.task_plans))

    st.divider()

    # Example Queries
    st.subheader("Example Queries")

    example_queries = [
        "What is the impact of adding promo codes?",
        "Analyze the integration flow for payment module",
        "What systems are affected by the new API?",
        "Review the code structure and recommendations"
    ]

    for i, query in enumerate(example_queries):
        if st.button(query, use_container_width=True, key=f"example_{i}"):
            st.session_state.input_query = query
            st.rerun()

    st.divider()

    # Clear History
    if st.button("Clear History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ============================================================================
# Main Header
# ============================================================================

st.title("Orchestrator Chat")
st.markdown("*Connect to your LangGraph orchestrator agent*")

# ============================================================================
# Messages Display
# ============================================================================

messages_container = st.container()

with messages_container:
    for i, msg in enumerate(st.session_state.messages):
        if msg["type"] == "user":
            st.markdown(f"**You** ({msg.get('timestamp', '')})")
            st.markdown(f"> {msg['content']}")
            st.divider()

        elif msg["type"] == "assistant":
            st.markdown(f"**Orchestrator** ({msg.get('timestamp', '')})")

            # Status
            status = msg.get("status", "pending")
            if status == "complete":
                st.success("Status: Completed")
            elif status == "error":
                st.error("Status: Error")
            else:
                st.info("Status: Processing")

            # Main response
            st.markdown(msg.get("content", ""))

            # Create tabs for different sections (INSTEAD OF NESTED EXPANDERS)
            tab1, tab2, tab3, tab4 = st.tabs(["Plan", "Order", "Results", "Error"])

            with tab1:
                if msg.get("task_plan"):
                    display_task_plan(msg["task_plan"])
                else:
                    st.write("No task plan available")

            with tab2:
                if msg.get("execution_order"):
                    st.write("**Agents will execute in this order:**")
                    for idx, agent in enumerate(msg["execution_order"], 1):
                        st.write(f"{idx}. {agent}")
                else:
                    st.write("No execution order available")

            with tab3:
                if msg.get("results"):
                    # Display each agent result WITHOUT nesting
                    results = msg["results"]
                    for agent_name, result in results.items():
                        display_agent_result(agent_name, result)
                else:
                    st.write("No results available")

            with tab4:
                if msg.get("error"):
                    st.error(f"Error occurred: {msg['error']}")
                else:
                    st.write("No errors")

            st.divider()

# ============================================================================
# Input Area
# ============================================================================

# Input form
col1, col2 = st.columns([0.9, 0.1])

with col1:
    user_input = st.text_input(
        "Ask orchestrator...",
        placeholder="What is the impact of adding promo codes?",
        key="user_input",
        label_visibility="collapsed"
    )

with col2:
    submit_button = st.button("Send", use_container_width=True)

# ============================================================================
# Process Input
# ============================================================================

if submit_button and user_input:
    # Add user message
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "type": "user",
        "content": user_input,
        "timestamp": timestamp
    })

    # Show loading state
    with st.spinner("Processing..."):
        # Call orchestrator
        result = call_orchestrator(user_input, st.session_state.thread_id)

        if result:
            # Parse task plan if present
            task_plan = None
            if result.get("task_plan"):
                try:
                    task_plan = json.loads(result["task_plan"]) if isinstance(result["task_plan"], str) else result["task_plan"]
                    st.session_state.task_plans.append(task_plan)
                except:
                    task_plan = None

            # Add assistant message
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.messages.append({
                "type": "assistant",
                "content": result.get("error") or "Task completed successfully",
                "status": result.get("status", "pending"),
                "task_plan": task_plan,
                "execution_order": result.get("execution_order"),
                "results": result.get("results"),
                "error": result.get("error"),
                "timestamp": timestamp
            })

            # Add to execution history
            st.session_state.execution_history.append({
                "query": user_input,
                "thread_id": st.session_state.thread_id,
                "timestamp": timestamp,
                "status": result.get("status"),
                "agents": result.get("execution_order", [])
            })

    st.rerun()

# ============================================================================
# Footer
# ============================================================================

st.divider()
st.markdown("Orchestrator Chat v1.0 - Built with Streamlit | API: /orchestrate")
