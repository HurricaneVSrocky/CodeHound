import agent_tools
import re

print("==== CodeHound AI Agent 模拟演示 ====\n")

print("[AI 思考]: 收到报错信息 'main 函数发生崩溃'。我要先找到 main 函数的 Node ID。")
print(">> 工具调用: find_node_by_name('main')")
res1 = agent_tools.find_node_by_name('main')
print(res1)
print("\n-------------------------------------------------\n")

# Dynamically extract main node id from dummy_project
main_id = None
for line in res1.split('\n'):
    if "tests/dummy_project/main.cpp" in line:
        match = re.search(r"Node ID: (\d+)", line)
        if match:
            main_id = int(match.group(1))
            break

if main_id is None:
    print("Could not find dummy_project main.")
    exit(1)

print(f"[AI 思考]: 看来 Node ID: {main_id} 是我们要找的 dummy_project 的 main 函数 (根据文件路径筛选)。")
print(f">> 工具调用: get_node_relations(node_id={main_id}, depth=1, direction=1) # 1 代表 Outgoing (它调用了谁)")
res2 = agent_tools.get_node_relations(main_id, depth=1, direction=1)
print(res2)
print("\n-------------------------------------------------\n")

print("[AI 思考]: main 函数调用了 interactWithDog，并且调用了一个极其可疑的 dangerousAction！我要深挖 dangerousAction。")
print(">> 工具调用: find_node_by_name('dangerousAction')")
res3 = agent_tools.find_node_by_name('dangerousAction')
print(res3)
print("\n-------------------------------------------------\n")

danger_id = None
for line in res3.split('\n'):
    match = re.search(r"Node ID: (\d+)", line)
    if match:
        danger_id = int(match.group(1))
        break

if danger_id:
    print(f"[AI 思考]: 找到了 dangerousAction 的 Node ID 是 {danger_id}。我看看它到底干了什么危险操作。")
    print(f">> 工具调用: get_node_relations(node_id={danger_id}, depth=1, direction=1)")
    res4 = agent_tools.get_node_relations(danger_id, depth=1, direction=1)
    print(res4)
    print("\n-------------------------------------------------\n")

    print("[AI 思考]: 破案了！dangerousAction 函数对一个名为 DangerPointer 的变量执行了 Writes (写入) 操作！")
    print(">> 最终结论: 经查，导致崩溃的根本原因是 main() 函数调用了 Dog::dangerousAction()，而该函数在未分配内存的情况下尝试写入全局指针 DangerPointer。")
