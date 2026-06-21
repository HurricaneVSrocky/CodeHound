import os
import sys

# Load C++ GraphEngine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../build/Release')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../build')))

engine = None
try:
    import codegraph_engine
    engine = codegraph_engine.GraphEngine()
    bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../graph_data.bin'))
    if os.path.exists(bin_path):
        engine.load_from_file(bin_path)
    else:
        print(f"Warning: {bin_path} not found.")
except Exception as e:
    print(f"Failed to load C++ engine: {e}")

def find_node_by_name(name: str) -> str:
    """
    搜索图谱中的节点名。获取某个函数、变量或类的全局 ID 及其详细信息。
    在调用 get_node_relations 之前，必须先用此工具找到目标 Node ID。
    
    Args:
        name: 模糊或精确搜索的关键字 (例如函数名 'main', 'dangerousAction' 等)。
        
    Returns:
        包含找到的节点 ID、名称、所在文件和行号的文本列表。
    """
    if not engine:
        return "Error: GraphEngine is not loaded."
    
    nodes = engine.search_nodes(name, 50)
    if not nodes:
        return f"未找到任何匹配 '{name}' 的节点。"
    
    types = {1: 'File', 2: 'Class', 3: 'Struct', 4: 'Function', 5: 'Method', 6: 'Variable'}
    result = [f"Found {len(nodes)} nodes matching '{name}':"]
    for n in nodes:
        t_name = types.get(n.type, f"Unknown({n.type})")
        result.append(f"  - Node ID: {n.id} | Type: {t_name} | Name: {n.name} | Location: {n.file_path}:{n.start_line}")
        
    return "\n".join(result)

def get_node_relations(node_id: int, depth: int = 1, direction: int = 0) -> str:
    """
    获取指定节点在代码中的依赖子图。可以查询函数的调用链，或者变量在哪里被读/写。
    
    Args:
        node_id: 通过 find_node_by_name 获取的数字 ID。
        depth: 遍历深度 (通常填 1 或 2，防止结果过长)。
        direction: 关系方向。0 表示 Both (入边和出边)，1 表示 Outgoing (它主动发起的调用/修改)，2 表示 Incoming (谁调用了它/谁修改了它)。
        
    Returns:
        一系列边关系，例如 `main --[Calls]--> dangerousAction`。
    """
    if not engine:
        return "Error: GraphEngine is not loaded."
        
    nodes, edges = engine.get_relations(node_id, depth, direction)
    if not edges:
        return f"Node {node_id} 没有发现相关依赖边。"
        
    node_map = {n.id: n.name for n in nodes}
    edge_types = {1: 'Includes', 2: 'Inherits', 3: 'Calls', 4: 'Reads', 5: 'Writes'}
    
    result = [f"Dependency relations for Node ID {node_id} (Depth {depth}, Direction {direction}):"]
    
    for e in edges:
        src = node_map.get(e.source_id, f"ID:{e.source_id}")
        tgt = node_map.get(e.target_id, f"ID:{e.target_id}")
        rel = edge_types.get(e.type, f"Rel:{e.type}")
        result.append(f"  - {src} --[{rel}]--> {tgt}")
        
    return "\n".join(result)

def find_node_by_location(file_path: str, line_number: int) -> str:
    """
    根据文件名和行号在代码图谱中检索并定位对应的节点。
    适用于 AI 从崩溃日志、调用栈中提取了 `file:line` 信息但不知道具体函数或变量名时。
    
    Args:
        file_path: 文件路径（支持模糊/相对子串匹配，例如 'main.cpp'）。
        line_number: 源码中的行号。
        
    Returns:
        包含找到的节点 ID、名称、所在文件和行号的文本列表。
    """
    if not engine:
        return "Error: GraphEngine is not loaded."
        
    nodes = engine.find_nodes_by_location(file_path, line_number)
    if not nodes:
        return f"未找到在文件 '{file_path}' 的第 {line_number} 行附近匹配的节点。"
        
    types = {1: 'File', 2: 'Class', 3: 'Struct', 4: 'Function', 5: 'Method', 6: 'Variable'}
    result = [f"Found {len(nodes)} nodes matching location '{file_path}:{line_number}':"]
    for n in nodes:
        t_name = types.get(n.type, f"Unknown({n.type})")
        result.append(f"  - Node ID: {n.id} | Type: {t_name} | Name: {n.name} | Location: {n.file_path}:{n.start_line}")
        
    return "\n".join(result)

def persist_graph() -> str:
    """
    持久化内存中最新的代码图谱数据到磁盘文件（graph_data.bin）。
    适用于当 AST 节点或关联关系发生变化，需要将当前图谱落盘归档时。
    
    Returns:
        持久化操作的结果消息。
    """
    if not engine:
        return "Error: GraphEngine is not loaded."
        
    bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../graph_data.bin'))
    success = engine.save_to_file(bin_path)
    if success:
        return f"成功将最新的内存代码图谱持久化到磁盘：{bin_path}"
    else:
        return "持久化失败，写入文件出错。"
