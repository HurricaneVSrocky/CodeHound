#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <shared_mutex>
#include <utility>

namespace CodeGraph {

// 前置声明 flatbuffers 生成的类型
struct Node;
struct Edge;
struct GraphPayload;

// 对外暴露的 C++ 节点结构
struct CxxNode {
    int id;
    int type;
    std::string name;
    std::string file_path;
    int start_line;
};

// 对外暴露的 C++ 边结构
struct CxxEdge {
    int source_id;
    int target_id;
    int type;
};

class GraphEngine {
public:
    GraphEngine();
    ~GraphEngine();

    // 从二进制文件中加载图谱 (返回 true 成功)
    bool load_from_file(const std::string& filepath);

    // 应用增量更新
    bool apply_delta(const std::string& filepath);

    // 关键字检索节点 (精确匹配或包含匹配均可)
    std::vector<CxxNode> search_nodes(const std::string& keyword, int limit = 50);

    // 获取特定项目路径下的所有节点（顶层节点）
    std::vector<CxxNode> get_project_nodes(const std::string& project_path_substring);
    
    // Get only top-level project nodes (nodes without incoming 'Contains' edges)
    std::vector<CxxNode> get_top_level_project_nodes(const std::string& project_path_substring);

    // 获取节点的上下游邻居
    // direction: 0 = Both, 1 = Out (它调用的), 2 = In (调用它的)
    std::pair<std::vector<CxxNode>, std::vector<CxxEdge>> get_relations(int node_id, int depth, int direction = 0);

    // 根据文件名子串和行号定位最接近或精确匹配的节点
    std::vector<CxxNode> find_nodes_by_location(const std::string& file_path_substring, int line_number);

    // 将当前的内存图谱持久化写入二进制文件
    bool save_to_file(const std::string& filepath);

private:
    std::shared_mutex rw_mutex_;

    // 内存数据存储
    std::unordered_map<int, CxxNode> nodes_;
    
    // 邻接表：source_id -> list of edges
    std::unordered_map<int, std::vector<CxxEdge>> out_edges_;
    // 逆向邻接表：target_id -> list of edges
    std::unordered_map<int, std::vector<CxxEdge>> in_edges_;
};

} // namespace CodeGraph
