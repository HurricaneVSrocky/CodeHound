#pragma once
#include <clang-c/Index.h>
#include <string>
#include <vector>
#include <unordered_map>
#include "../../engine/src/graph_generated.h"

using namespace CodeGraph;

struct NodeData {
    int32_t id;
    NodeType type;
    std::string name;
    std::string file_path;
    int32_t start_line;
};

struct EdgeData {
    int32_t source_id;
    int32_t target_id;
    EdgeType type;
};

class ASTVisitor {
public:
    void Visit(CXCursor root_cursor);
    void Save(const std::string& out_path);

private:
    static CXChildVisitResult VisitNode(CXCursor cursor, CXCursor parent, CXClientData client_data);

    int32_t GetOrAddNode(CXCursor cursor);
    std::string GetCursorName(CXCursor cursor);
    std::string GetCursorSpelling(CXCursor cursor);

    std::unordered_map<std::string, int32_t> usr_to_id;
    std::vector<NodeData> nodes;
    std::vector<EdgeData> edges;
    int32_t next_id = 1;
};
