import sys
import os

# 假设执行此脚本前，已经通过 flatc 生成了 Python 文件到当前或上级目录
# 比如 CMake 构建目录下会有 CodeGraph/ 文件夹
# 我们尝试将其加入 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../build'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import flatbuffers
    import CodeGraph.NodeType as NodeType
    import CodeGraph.EdgeType as EdgeType
    import CodeGraph.Node as Node
    import CodeGraph.Edge as Edge
    import CodeGraph.GraphPayload as GraphPayload
except ImportError:
    print("Warning: FlatBuffers python module or generated CodeGraph not found.")
    print("Please make sure you have run CMake or flatc to generate the python files.")
    print("And 'pip install flatbuffers'")
    sys.exit(1)

def build_node(builder, n_id, n_type, name, file_path, start_line):
    name_str = builder.CreateString(name)
    file_path_str = builder.CreateString(file_path)
    
    Node.Start(builder)
    Node.AddId(builder, n_id)
    Node.AddType(builder, n_type)
    Node.AddName(builder, name_str)
    Node.AddFilePath(builder, file_path_str)
    Node.AddStartLine(builder, start_line)
    return Node.End(builder)


def main():
    builder = flatbuffers.Builder(1024)

    nodes = []
    # 创建一些测试节点
    # 1. src/main.cpp
    nodes.append(build_node(builder, 1, NodeType.NodeType().File, "src/main.cpp", "src/main.cpp", 1))
    # 2. class App
    nodes.append(build_node(builder, 2, NodeType.NodeType().Class, "App", "src/main.cpp", 10))
    # 3. int main()
    nodes.append(build_node(builder, 3, NodeType.NodeType().Function, "main", "src/main.cpp", 50))
    # 4. App::init()
    nodes.append(build_node(builder, 4, NodeType.NodeType().Method, "App::init", "src/main.cpp", 12))
    # 5. App::run()
    nodes.append(build_node(builder, 5, NodeType.NodeType().Method, "App::run", "src/main.cpp", 20))
    # 6. Global var Config
    nodes.append(build_node(builder, 6, NodeType.NodeType().Variable, "g_config", "src/main.cpp", 5))

    # 构建 Node 向量
    GraphPayload.StartNodesVector(builder, len(nodes))
    for n in reversed(nodes):
        builder.PrependUOffsetTRelative(n)
    nodes_vec = builder.EndVector()

    # 构建 Edge 向量 (从后往前添加)
    GraphPayload.StartEdgesVector(builder, 4)
    # 4. App::run -> Reads -> g_config
    Edge.CreateEdge(builder, 5, 6, EdgeType.EdgeType().Reads)
    # 3. App::init -> Writes -> g_config
    Edge.CreateEdge(builder, 4, 6, EdgeType.EdgeType().Writes)
    # 2. main -> Calls -> App::run
    Edge.CreateEdge(builder, 3, 5, EdgeType.EdgeType().Calls)
    # 1. main -> Calls -> App::init
    Edge.CreateEdge(builder, 3, 4, EdgeType.EdgeType().Calls)
    edges_vec = builder.EndVector()

    # 构建 Root
    GraphPayload.Start(builder)
    GraphPayload.AddVersion(builder, 1)
    GraphPayload.AddNodes(builder, nodes_vec)
    GraphPayload.AddEdges(builder, edges_vec)
    payload = GraphPayload.End(builder)

    builder.Finish(payload)

    # 写入二进制文件
    output_path = os.path.join(os.path.dirname(__file__), '../dummy_data.bin')
    with open(output_path, 'wb') as f:
        f.write(builder.Output())

    print(f"Mock data generated successfully at {output_path}")

if __name__ == "__main__":
    main()
