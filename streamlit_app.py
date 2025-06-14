import streamlit as st
import os
import json
from typing import List
import litellm

# --- 1. DEFINE AGENT TOOLS & RULES (No changes here) ---
# ... (all your tool functions and schemas are still here and perfect)
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

# Mapping and tool schemas...
tool_functions = { "list_files": list_files, "read_file": read_file, "multiply_numbers": multiply_numbers, "terminate": terminate }
tools = [
    {"type": "function", "function": {"name": "list_files", "description": "Returns a list of available files.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Reads the content of a specified file.", "parameters": {"type": "object", "properties": {"file_name": {"type": "string"}}, "required": ["file_name"]}}},
    {"type": "function", "function": {"name": "multiply_numbers", "description": "Multiplies two numbers. Use this for any calculation.", "parameters": {"type": "object", "properties": {"num1": {"type": "number"}, "num2": {"type": "number"}}, "required": ["num1", "num2"]}}},
    {"type": "function", "function": {"name": "terminate", "description": "Terminates the conversation when the user's request is fully answered. Prints the final message for the user.", "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
]
agent_rules = {"role": "system", "content": "You are an AI agent that can perform tasks by using available tools. If a user asks a question that requires calculation, use the multiply_numbers tool. If a user asks about files, first list the files before reading them. When you are done, terminate the conversation by using the 'terminate' tool with a final, friendly message. Always provide the answer and then terminate in the same step if possible."}


# --- 2. SET UP STREAMLIT UI & SECRETS ---
st.title("🤖 Agent Chatbot with Tools")
st.write("This chatbot uses an agent with tools to answer questions. It can do math and read files. Try asking: 'What is 123 times 45?'")

if "OPENROUTER_API_KEY" not in st.secrets:
    st.error("API key not found. Please add it to your secrets.")
    st.info("Create a file at .streamlit/secrets.toml with the content: OPENROUTER_API_KEY = 'your_key_here'")
    st.stop()

api_key = st.secrets["OPENROUTER_API_KEY"]
os.environ['OPENROUTER_API_KEY'] = api_key
litellm.set_verbose = False

# --- 3. INITIALIZE & DISPLAY CHAT HISTORY ---
if "messages" not in st.session_state:
    st.session_state.messages = [agent_rules]

# === NEW: Display history with custom avatars ===
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    
    avatar = "👤" if message["role"] == "user" else "🤖"
    
    # Check for our custom tool messages to assign special avatars
    if message["role"] == "assistant" and "⚙️ **Tool:**" in message["content"]:
        avatar = "⚙️"
    if message["role"] == "assistant" and "📋 **Result:**" in message["content"]:
        avatar = "📋"
    if message["role"] == "assistant" and "✅ **Final Answer:**" in message["content"]:
        avatar = "✅"

    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"], unsafe_allow_html=True)


# --- 4. THE AGENT LOGIC (WITH UI ENHANCEMENTS) ---
if prompt := st.chat_input("What would you like me to do?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    max_iterations = 10
    for i in range(max_iterations):
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
                    final_message_content = f"✅ **Final Answer:** {tool_args.get('message', 'All done!')}"
                    with st.chat_message("assistant", avatar="✅"):
                        st.markdown(final_message_content, unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": final_message_content})
                    break 
                
                # Display "Thinking about using a tool" message
                thinking_message_content = f"⚙️ **Tool:** `{tool_name}` <br> 📝 **Arguments:** `{tool_args}`"
                with st.chat_message("assistant", avatar="⚙️"):
                    st.markdown(thinking_message_content, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": thinking_message_content})

                # Execute the tool and get the result
                try:
                    result = tool_functions[tool_name](**tool_args)
                    tool_response_content = json.dumps({"result": result})
                except Exception as e:
                    tool_response_content = json.dumps({"error": str(e)})

                # === NEW: Display the raw tool result ===
                tool_result_display_content = f"📋 **Result:** `{tool_response_content}`"
                with st.chat_message("assistant", avatar="📋"):
                    st.markdown(tool_result_display_content, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": tool_result_display_content})
                
                # Add the actual tool result for the agent to see in the next loop
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
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            break

    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.warning("The agent reached its iteration limit.")