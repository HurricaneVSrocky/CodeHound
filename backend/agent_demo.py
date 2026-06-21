import os
import sys

# Import our custom CodeHound AI tools
import agent_tools

def mock_ai_loop():
    """
    如果用户没有提供 API Key，提供一个交互式的模拟调试流程，
    验证 Tool 是否能正确返回自然语言上下文。
    """
    print("==================================================")
    print("CodeHound Agent Tools CLI (Manual Mode)")
    print("==================================================")
    print("Tools available:")
    print("1: find_node_by_name(name)")
    print("2: get_node_relations(node_id, depth=1, direction=0)")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            cmd = input("Agent Tool> ").strip()
            if cmd.lower() in ('exit', 'quit'):
                break
                
            if cmd.startswith("1"):
                name = input("  Enter 'name': ").strip()
                print(agent_tools.find_node_by_name(name))
            elif cmd.startswith("2"):
                node_id = int(input("  Enter 'node_id': ").strip())
                res = agent_tools.get_node_relations(node_id, 1, 0)
                print(res)
            else:
                print("Invalid tool index. Choose 1 or 2.")
        except Exception as e:
            print(f"Error: {e}")

def run_gemini_agent():
    """
    使用真实的 Gemini 模型来执行 Function Calling，自主排查段错误。
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Please install google-genai: pip install google-genai")
        return
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY environment variable is not set.")
        print("Switching to manual Tool CLI mode...")
        mock_ai_loop()
        return

    print("Initializing Gemini Agent with CodeHound Tools...")
    client = genai.Client()
    
    prompt = """
    你是一个负责分析 C++ 代码的高级 AI 专家。
    我们有一个 dummy_project 发生了一次严重的 Crash (段错误)。
    
    用户提供的线索：
    "程序执行 main.cpp 中的 main 函数时，似乎触发了一个未定义的崩溃。请帮我找出根本原因。"
    
    你被赋予了图谱工具能力，请：
    1. 用 find_node_by_name 搜索 'main' 函数，获取其 node_id。
    2. 用 get_node_relations 查看 'main' 调用了什么（它可能调用了危险的函数）。
    3. 继续使用 get_node_relations 追踪嫌疑函数，看它修改或读取了哪些变量。
    4. 结合常识，指出具体是哪一行或哪个变量导致了 Crash。
    
    请展示你一步步调研的过程。
    """
    
    tools = [agent_tools.find_node_by_name, agent_tools.get_node_relations]
    
    print("\n--- Agent Task Prompt ---")
    print(prompt.strip())
    print("-------------------------\n")
    print("Agent is thinking and calling tools autonomously...\n")
    
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            temperature=0.2,
            tools=tools,
        )
    )
    
    # 简单的自动工具调用 Loop (使用 sendMessage，自动响应 Tool Call)
    response = chat.send_message(prompt)
    
    # In genai SDK, send_message handles automatic function calling loop natively if config permits,
    # or we handle it if needed. For simplicity, we just print the final response or the tool calls.
    if response.text:
        print("Agent Conclusion:")
        print(response.text)
    elif response.function_calls:
        print("Agent requested to call functions manually (SDK requires manual loop).")
        for call in response.function_calls:
            print(f"- Call: {call.name}({call.args})")

if __name__ == "__main__":
    run_gemini_agent()
