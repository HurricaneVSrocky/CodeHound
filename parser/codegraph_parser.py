import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/schema')))
import flatbuffers
import CodeGraph.Node
import CodeGraph.Edge
import CodeGraph.GraphPayload
import CodeGraph.NodeType
import CodeGraph.EdgeType

from clang.cindex import Index, CursorKind, Config
import clang
clang_dir = os.path.dirname(clang.__file__)
dll_path = os.path.join(clang_dir, 'native', 'libclang.dll')
if os.path.exists(dll_path):
    Config.set_library_file(dll_path)

class ASTVisitor:
    def __init__(self, project_root=""):
        self.usr_to_id = {}
        self.nodes = []
        self.edges = []
        self.next_id = 1
        # Convert project root to normalized absolute path
        self.project_root = os.path.abspath(project_root).replace("\\", "/") if project_root else ""

    def get_or_add_node(self, cursor):
        usr = cursor.get_usr()
        if not usr:
            usr = cursor.spelling
            if not usr:
                return 0
        
        if usr in self.usr_to_id:
            return self.usr_to_id[usr]

        kind = cursor.kind
        node_type = CodeGraph.NodeType.NodeType().Unknown
        if kind == CursorKind.CLASS_DECL:
            node_type = CodeGraph.NodeType.NodeType().Class
        elif kind == CursorKind.STRUCT_DECL:
            node_type = CodeGraph.NodeType.NodeType().Struct
        elif kind == CursorKind.CXX_METHOD:
            node_type = CodeGraph.NodeType.NodeType().Method
        elif kind == CursorKind.FUNCTION_DECL:
            node_type = CodeGraph.NodeType.NodeType().Function
        elif kind == CursorKind.VAR_DECL or kind == CursorKind.FIELD_DECL:
            node_type = CodeGraph.NodeType.NodeType().Variable
        elif kind == CursorKind.TRANSLATION_UNIT:
            node_type = CodeGraph.NodeType.NodeType().File
        else:
            return 0

        node_id = self.next_id
        self.next_id += 1
        self.usr_to_id[usr] = node_id

        loc = cursor.location
        file_path = loc.file.name if loc.file else ""
        start_line = loc.line if loc.line else 0

        # Replace backslashes for consistency
        file_path = file_path.replace("\\", "/")
        abs_file_path = os.path.abspath(file_path).replace("\\", "/") if file_path else ""

        # 【核心过滤逻辑】：如果设置了项目根目录，且该节点不属于该根目录（例如系统头文件），则直接忽略
        if self.project_root and not abs_file_path.startswith(self.project_root):
            return 0

        self.nodes.append({
            "id": node_id,
            "type": node_type,
            "name": cursor.spelling,
            "file_path": file_path,
            "start_line": start_line
        })
        return node_id

    def visit(self, cursor, parent=None):
        kind = cursor.kind

        if kind.is_declaration():
            self.get_or_add_node(cursor)

        if kind == CursorKind.CALL_EXPR:
            referenced = cursor.referenced
            if referenced:
                target_id = self.get_or_add_node(referenced)
                source_id = self.get_or_add_node(parent) if parent else 0
                if source_id > 0 and target_id > 0:
                    self.edges.append((source_id, target_id, CodeGraph.EdgeType.EdgeType().Calls))

        elif kind == CursorKind.CXX_BASE_SPECIFIER:
            referenced = cursor.referenced
            if referenced:
                target_id = self.get_or_add_node(referenced)
                source_id = self.get_or_add_node(parent) if parent else 0
                if source_id > 0 and target_id > 0:
                    self.edges.append((source_id, target_id, CodeGraph.EdgeType.EdgeType().Inherits))

        elif kind == CursorKind.DECL_REF_EXPR:
            referenced = cursor.referenced
            if referenced and (referenced.kind == CursorKind.VAR_DECL or referenced.kind == CursorKind.FIELD_DECL):
                target_id = self.get_or_add_node(referenced)
                source_id = self.get_or_add_node(parent) if parent else 0
                if source_id > 0 and target_id > 0:
                    self.edges.append((source_id, target_id, CodeGraph.EdgeType.EdgeType().Reads))

        for child in cursor.get_children():
            p = parent
            if child.kind.is_declaration():
                p = child
            elif not p and kind.is_declaration():
                p = cursor
            self.visit(child, p)

    def save(self, out_path):
        builder = flatbuffers.Builder(1024)

        fb_nodes = []
        for n in self.nodes:
            name_str = builder.CreateString(n["name"])
            path_str = builder.CreateString(n["file_path"])
            
            CodeGraph.Node.NodeStart(builder)
            CodeGraph.Node.NodeAddId(builder, n["id"])
            CodeGraph.Node.NodeAddType(builder, n["type"])
            CodeGraph.Node.NodeAddName(builder, name_str)
            CodeGraph.Node.NodeAddFilePath(builder, path_str)
            CodeGraph.Node.NodeAddStartLine(builder, n["start_line"])
            fb_nodes.append(CodeGraph.Node.NodeEnd(builder))
            
        CodeGraph.GraphPayload.GraphPayloadStartNodesVector(builder, len(fb_nodes))
        for n in reversed(fb_nodes):
            builder.PrependUOffsetTRelative(n)
        nodes_vec = builder.EndVector()

        CodeGraph.GraphPayload.GraphPayloadStartEdgesVector(builder, len(self.edges))
        for e in reversed(self.edges):
            CodeGraph.Edge.CreateEdge(builder, e[0], e[1], e[2])
        edges_vec = builder.EndVector()

        CodeGraph.GraphPayload.GraphPayloadStart(builder)
        CodeGraph.GraphPayload.GraphPayloadAddVersion(builder, 1)
        CodeGraph.GraphPayload.GraphPayloadAddNodes(builder, nodes_vec)
        CodeGraph.GraphPayload.GraphPayloadAddEdges(builder, edges_vec)
        root = CodeGraph.GraphPayload.GraphPayloadEnd(builder)

        builder.Finish(root)
        
        with open(out_path, "wb") as f:
            f.write(builder.Output())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python codegraph_parser.py <file> [--update] [--out <file>]")
        sys.exit(1)

    file_path = sys.argv[1]
    out_file = "graph_data.bin"

    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        out_file = sys.argv[idx+1]

    # Convert relative project path to absolute for filtering
    project_root = os.path.abspath(file_path)

    index = Index.create()
    visitor = ASTVisitor(project_root=project_root)
    
    if os.path.isdir(file_path):
        for root, dirs, files in os.walk(file_path):
            for file in files:
                if file.endswith(('.cpp', '.c')):
                    full_path = os.path.join(root, file)
                    tu = index.parse(full_path, args=['-std=c++17', f'-I{file_path}'])
                    visitor.visit(tu.cursor)
    else:
        tu = index.parse(file_path, args=['-std=c++17'])
        visitor.visit(tu.cursor)

    visitor.save(out_file)
    print(f"Parsed {file_path}. Saved to {out_file}")
