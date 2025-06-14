import streamlit as st
import os
import json
from typing import List
import litellm

# --- 1. DEFINE AGENT TOOLS & RULES (No changes here) ---

# Tool Functions
def list_files() -> List[str]:
    """List files in the current directory."""
    return ["project_plan.md", "data_report.csv", "apu_the_cat.jpg"]

def read_file(file_name: str) -> str:
    """Read a file's contents."""
    if file_name == "project_plan.md":
        return "Project Plan: The main goal is to build a Streamlit chatbot."
    else:
        return f"Error: File '{file_name}' not found or cannot be read."

def multiply_numbers(num1: float, num2: float) -> float:
    """Multiply two numbers."""
    return num1 * num2

def terminate(message: str) -> None:
    """Terminate the agent loop and provide a final message."""
    pass

# Mapping and tool schemas... (rest of the section is identical)
tool_functions = {
    "list_files": list_files,
    "read_file": read_file,
    "multiply_numbers": multiply_numbers,
    "terminate": terminate,
}
tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Returns a list of available files.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a specified file.",
            "parameters": {
                "type": "object",
                "properties": {"file_name": {"type": "string"}},
                "required": ["file_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply_numbers",
            "description": "Multiplies two numbers. Use this for any calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "num1": {"type": "number"},
                    "num2": {"type": "number"}
                },
                "required": ["num1", "num2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "terminate",
            "description": "Terminates the conversation when the user's request is fully answered. Prints the final message for the user.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        },
    },
]
agent_rules = {
    "role": "system",
    "content": """
You are an AI agent that can perform tasks by using available tools.
If a user asks a question that requires calculation, use the multiply_numbers tool.
If a user asks about files, first list the files before reading them.
When you are done, terminate the conversation by using the "terminate" tool with a final, friendly message.
Always provide the answer and then terminate in the same step if possible.
""",
}

# --- 2. SET UP STREAMLIT UI & SECRETS ---

st.title("🤖 Agent Chatbot with Tools")
st.write(
    "This chatbot uses an agent with tools to answer questions. "
    "It can do math and read files. Try asking: 'What is 123 times 45?'"
)

# === MODIFIED SECTION: READ KEY FROM st.secrets ===
# Check for the API key in st.secrets.toml.
if "OPENROUTER_API_KEY" not in st.secrets:
    st.error("API key not found. Please add it to your secrets.")
    st.info("Create a file at .streamlit/secrets.toml with the content: OPENROUTER_API_KEY = 'your_key_here'")
    st.stop() # Stop the app if the key is missing

# If the key exists, set it for litellm and continue with the app.
api_key = st.secrets["OPENROUTER_API_KEY"]
os.environ['OPENROUTER_API_KEY'] = api_key
litellm.set_verbose = False # Keep the console clean
# === END OF MODIFIED SECTION ===

# --- 3. INITIALIZE & DISPLAY CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = [agent_rules]

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- 4. THE AGENT LOGIC (No changes here) ---
if prompt := st.chat_input("What would you like me to do?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    max_iterations = 10
    for i in range(max_iterations):
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = litellm.completion(
                    model="openrouter/deepseek/deepseek-chat-v3-0324:free",
                    messages=st.session_state.messages,
                    tools=tools,
                )
            response_message = response.choices[0].message

        if response_message.tool_calls:
            st.session_state.messages.append(response_message)
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == "terminate":
                    final_message = tool_args.get("message", "All done!")
                    st.markdown(f"✅ **Final Answer:** {final_message}")
                    st.session_state.messages.append({"role": "assistant", "content": final_message})
                    break 
                
                with st.chat_message("assistant"):
                    st.markdown(f" Mmh... I need to use a tool. <br> ⚙️ **Tool:** `{tool_name}` <br> 📝 **Arguments:** `{tool_args}`", unsafe_allow_html=True)

                try:
                    result = tool_functions[tool_name](**tool_args)
                    tool_response_content = json.dumps({"result": result})
                except Exception as e:
                    result = f"Error: {e}"
                    tool_response_content = json.dumps({"error": result})

                st.session_state.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_response_content,
                })
            
            if tool_name == "terminate":
                break
        else:
            final_response = response_message.content
            st.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            break

    else:
        with st.chat_message("assistant"):
            st.warning("The agent reached its iteration limit. Please try rephrasing your request.")