#include "graph_engine.h"
#include <fstream>
#include <iostream>
#include <queue>
#include <unordered_set>

// 这个头文件由 flatc 根据 schema 自动生成，需要在 CMake 构建时产生
#include "graph_generated.h"

namespace CodeGraph {

GraphEngine::GraphEngine() {}

GraphEngine::~GraphEngine() {}

bool GraphEngine::load_from_file(const std::string& filepath) {
    std::ifstream infile(filepath, std::ios::binary | std::ios::ate);
    if (!infile.is_open()) {
        std::cerr << "Failed to open " << filepath << std::endl;
        return false;
    }

    std::streamsize size = infile.tellg();
    infile.seekg(0, std::ios::beg);

    std::vector<char> buffer(size);
    if (!infile.read(buffer.data(), size)) {
        std::cerr << "Failed to read " << filepath << std::endl;
        return false;
    }

    // 解析 FlatBuffers
    auto payload = GetGraphPayload(buffer.data());
    if (!payload) {
        std::cerr << "Invalid GraphPayload data" << std::endl;
        return false;
    }

    std::unique_lock<std::shared_mutex> lock(rw_mutex_);
    
    // 清空旧数据
    nodes_.clear();
    out_edges_.clear();
    in_edges_.clear();

    // 填充节点
    if (payload->nodes()) {
        for (const auto* n : *payload->nodes()) {
            CxxNode cxx_node;
            cxx_node.id = n->id();
            cxx_node.type = static_cast<int>(n->type());
            cxx_node.name = n->name() ? n->name()->str() : "";
            cxx_node.file_path = n->file_path() ? n->file_path()->str() : "";
            cxx_node.start_line = n->start_line();
            
            nodes_[cxx_node.id] = cxx_node;
        }
    }

    // 填充边
    if (payload->edges()) {
        for (const auto* e : *payload->edges()) {
            CxxEdge cxx_edge;
            cxx_edge.source_id = e->source_id();
            cxx_edge.target_id = e->target_id();
            cxx_edge.type = static_cast<int>(e->type());

            out_edges_[cxx_edge.source_id].push_back(cxx_edge);
            in_edges_[cxx_edge.target_id].push_back(cxx_edge);
        }
    }

    std::cout << "Loaded Graph Engine. Nodes: " << nodes_.size() << " Edges: " << (payload->edges() ? payload->edges()->size() : 0) << std::endl;
    return true;
}

bool GraphEngine::apply_delta(const std::string& filepath) {
    std::ifstream infile(filepath, std::ios::binary | std::ios::ate);
    if (!infile.is_open()) {
        std::cerr << "Failed to open delta " << filepath << std::endl;
        return false;
    }

    std::streamsize size = infile.tellg();
    infile.seekg(0, std::ios::beg);
    std::vector<char> buffer(size);
    if (!infile.read(buffer.data(), size)) return false;

    auto payload = GetGraphPayload(buffer.data());
    if (!payload) return false;

    std::unique_lock<std::shared_mutex> lock(rw_mutex_);

    // 1. 收集将要更新的文件路径
    std::unordered_set<std::string> updated_files;
    if (payload->nodes()) {
        for (const auto* n : *payload->nodes()) {
            if (n->file_path() && n->file_path()->Length() > 0) {
                updated_files.insert(n->file_path()->str());
            }
        }
    }

    // 2. 找到所有需要删除的旧节点 ID
    std::unordered_set<int> ids_to_remove;
    for (auto it = nodes_.begin(); it != nodes_.end(); ) {
        if (updated_files.count(it->second.file_path)) {
            ids_to_remove.insert(it->first);
            it = nodes_.erase(it);
        } else {
            ++it;
        }
    }

    // 3. 清理边
    auto remove_edges = [&](std::unordered_map<int, std::vector<CxxEdge>>& edges_map) {
        for (auto it = edges_map.begin(); it != edges_map.end(); ) {
            if (ids_to_remove.count(it->first)) {
                it = edges_map.erase(it);
            } else {
                auto& vec = it->second;
                vec.erase(std::remove_if(vec.begin(), vec.end(), [&](const CxxEdge& e) {
                    return ids_to_remove.count(e.source_id) || ids_to_remove.count(e.target_id);
                }), vec.end());
                if (vec.empty()) {
                    it = edges_map.erase(it);
                } else {
                    ++it;
                }
            }
        }
    };
    remove_edges(out_edges_);
    remove_edges(in_edges_);

    // 4. 插入新节点
    if (payload->nodes()) {
        for (const auto* n : *payload->nodes()) {
            CxxNode cxx_node;
            cxx_node.id = n->id();
            cxx_node.type = static_cast<int>(n->type());
            cxx_node.name = n->name() ? n->name()->str() : "";
            cxx_node.file_path = n->file_path() ? n->file_path()->str() : "";
            cxx_node.start_line = n->start_line();
            nodes_[cxx_node.id] = cxx_node;
        }
    }

    // 5. 插入新边
    if (payload->edges()) {
        for (const auto* e : *payload->edges()) {
            CxxEdge cxx_edge;
            cxx_edge.source_id = e->source_id();
            cxx_edge.target_id = e->target_id();
            cxx_edge.type = static_cast<int>(e->type());
            out_edges_[cxx_edge.source_id].push_back(cxx_edge);
            in_edges_[cxx_edge.target_id].push_back(cxx_edge);
        }
    }

    std::cout << "Applied Delta. Total Nodes: " << nodes_.size() << std::endl;
    return true;
}

std::vector<CxxNode> GraphEngine::search_nodes(const std::string& keyword, int limit) {
    std::shared_lock<std::shared_mutex> lock(rw_mutex_);
    std::vector<CodeGraph::CxxNode> ret_nodes;

    for (const auto& kv : nodes_) {
        // 简单包含匹配
        if (keyword.empty() || kv.second.name.find(keyword) != std::string::npos) {
            ret_nodes.push_back(kv.second);
            if (ret_nodes.size() >= limit) {
                break;
            }
        }
    }
    return ret_nodes;
}

std::vector<CxxNode> GraphEngine::get_project_nodes(const std::string& project_path_substring) {
    std::shared_lock<std::shared_mutex> lock(rw_mutex_);
    std::vector<CodeGraph::CxxNode> ret_nodes;

    for (const auto& kv : nodes_) {
        if (kv.second.file_path.find(project_path_substring) != std::string::npos) {
            ret_nodes.push_back(kv.second);
        }
    }
    return ret_nodes;
}

std::vector<CxxNode> GraphEngine::get_top_level_project_nodes(const std::string& project_path_substring) {
    std::shared_lock<std::shared_mutex> lock(rw_mutex_);
    std::vector<CodeGraph::CxxNode> ret_nodes;
    
    // 收集所有被 Contains(4) 指向的 target_id，它们属于子节点，不能被当作顶层节点
    std::unordered_set<int> child_nodes;
    for (const auto& kv : out_edges_) {
        for (const auto& edge : kv.second) {
            if (edge.type == 4) { // Contains
                child_nodes.insert(edge.target_id);
            }
        }
    }

    for (const auto& kv : nodes_) {
        if (kv.second.file_path.find(project_path_substring) != std::string::npos) {
            // 如果不在 child_nodes 里面，说明它没有父节点
            if (child_nodes.find(kv.first) == child_nodes.end()) {
                ret_nodes.push_back(kv.second);
            }
        }
    }
    return ret_nodes;
}

std::pair<std::vector<CxxNode>, std::vector<CxxEdge>> GraphEngine::get_relations(int node_id, int depth, int direction) {
    std::shared_lock<std::shared_mutex> lock(rw_mutex_);
    
    std::vector<CxxNode> ret_nodes;
    std::vector<CxxEdge> ret_edges;

    if (nodes_.find(node_id) == nodes_.end()) {
        return {ret_nodes, ret_edges};
    }

    std::unordered_set<int> visited_nodes;
    std::unordered_set<int> visited_edges_hash; // 防止重复添加边

    // BFS 队列存储 {当前节点ID, 当前深度}
    std::queue<std::pair<int, int>> q;
    
    q.push({node_id, 0});
    visited_nodes.insert(node_id);

    while (!q.empty()) {
        auto [current_id, current_depth] = q.front();
        q.pop();

        ret_nodes.push_back(nodes_[current_id]);

        if (current_depth >= depth) continue;

        // 拓展出边 (direction 0 或 1)
        if ((direction == 0 || direction == 1) && out_edges_.count(current_id)) {
            for (const auto& edge : out_edges_.at(current_id)) {
                // edge hash (简化处理：source ^ target ^ type)
                int e_hash = edge.source_id ^ (edge.target_id << 1) ^ (edge.type << 2);
                if (visited_edges_hash.find(e_hash) == visited_edges_hash.end()) {
                    ret_edges.push_back(edge);
                    visited_edges_hash.insert(e_hash);
                }

                if (visited_nodes.find(edge.target_id) == visited_nodes.end()) {
                    visited_nodes.insert(edge.target_id);
                    q.push({edge.target_id, current_depth + 1});
                }
            }
        }

        // 拓展入边 (direction 0 或 2)
        if ((direction == 0 || direction == 2) && in_edges_.count(current_id)) {
            for (const auto& edge : in_edges_.at(current_id)) {
                int e_hash = edge.source_id ^ (edge.target_id << 1) ^ (edge.type << 2);
                if (visited_edges_hash.find(e_hash) == visited_edges_hash.end()) {
                    ret_edges.push_back(edge);
                    visited_edges_hash.insert(e_hash);
                }

                if (visited_nodes.find(edge.source_id) == visited_nodes.end()) {
                    visited_nodes.insert(edge.source_id);
                    q.push({edge.source_id, current_depth + 1});
                }
            }
        }
    }

    return {ret_nodes, ret_edges};
}

std::vector<CxxNode> GraphEngine::find_nodes_by_location(const std::string& file_path_substring, int line_number) {
    std::shared_lock<std::shared_mutex> lock(rw_mutex_);
    
    std::unordered_map<std::string, std::vector<CxxNode>> best_fit_per_file;
    std::unordered_map<std::string, int> min_diff_per_file;

    for (const auto& kv : nodes_) {
        const auto& node = kv.second;
        if (node.file_path.find(file_path_substring) == std::string::npos) {
            continue;
        }

        if (line_number <= 0) {
            best_fit_per_file[node.file_path].push_back(node);
            continue;
        }

        if (node.start_line <= line_number) {
            int diff = line_number - node.start_line;
            auto it = min_diff_per_file.find(node.file_path);
            if (it == min_diff_per_file.end()) {
                min_diff_per_file[node.file_path] = diff;
                best_fit_per_file[node.file_path] = {node};
            } else if (diff < it->second) {
                min_diff_per_file[node.file_path] = diff;
                best_fit_per_file[node.file_path] = {node};
            } else if (diff == it->second) {
                best_fit_per_file[node.file_path].push_back(node);
            }
        }
    }

    std::vector<CxxNode> result;
    for (const auto& kv : best_fit_per_file) {
        for (const auto& node : kv.second) {
            result.push_back(node);
        }
    }

    return result;
}

bool GraphEngine::save_to_file(const std::string& filepath) {
    std::unique_lock<std::shared_mutex> lock(rw_mutex_);
    
    flatbuffers::FlatBufferBuilder builder(1024);

    // 1. 构建 Nodes
    std::vector<flatbuffers::Offset<CodeGraph::Node>> fb_nodes;
    for (const auto& kv : nodes_) {
        const auto& node = kv.second;
        auto n_offset = CodeGraph::CreateNodeDirect(
            builder,
            node.id,
            static_cast<CodeGraph::NodeType>(node.type),
            node.name.c_str(),
            node.file_path.c_str(),
            node.start_line
        );
        fb_nodes.push_back(n_offset);
    }

    // 2. 构建 Edges
    std::vector<CodeGraph::Edge> fb_edges;
    for (const auto& kv : out_edges_) {
        for (const auto& edge : kv.second) {
            fb_edges.emplace_back(edge.source_id, edge.target_id, static_cast<CodeGraph::EdgeType>(edge.type));
        }
    }

    // 3. 构建 GraphPayload
    auto payload_offset = CodeGraph::CreateGraphPayloadDirect(
        builder,
        1, // version
        &fb_nodes,
        &fb_edges
    );

    builder.Finish(payload_offset);

    // 4. 保存到文件
    std::ofstream outfile(filepath, std::ios::binary);
    if (!outfile.is_open()) {
        std::cerr << "Failed to open " << filepath << " for writing." << std::endl;
        return false;
    }
    outfile.write(reinterpret_cast<const char*>(builder.GetBufferPointer()), builder.GetSize());
    return true;
}

} // namespace CodeGraph
