#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "graph_engine.h"

namespace py = pybind11;
using namespace CodeGraph;

PYBIND11_MODULE(codegraph_engine, m) {
    m.doc() = "C++ Graph Engine for CodeHound";

    // 绑定 CxxNode
    py::class_<CxxNode>(m, "Node")
        .def(py::init<>())
        .def_readwrite("id", &CxxNode::id)
        .def_readwrite("type", &CxxNode::type)
        .def_readwrite("name", &CxxNode::name)
        .def_readwrite("file_path", &CxxNode::file_path)
        .def_readwrite("start_line", &CxxNode::start_line);

    // 绑定 CxxEdge
    py::class_<CxxEdge>(m, "Edge")
        .def(py::init<>())
        .def_readwrite("source_id", &CxxEdge::source_id)
        .def_readwrite("target_id", &CxxEdge::target_id)
        .def_readwrite("type", &CxxEdge::type);

    // 绑定 GraphEngine
    py::class_<GraphEngine>(m, "GraphEngine")
        .def(py::init<>())
        .def("load_from_file", &GraphEngine::load_from_file, py::arg("filepath"))
        .def("apply_delta", &GraphEngine::apply_delta, py::arg("filepath"))
        .def("search_nodes", &GraphEngine::search_nodes, py::arg("keyword"), py::arg("limit") = 50)
        .def("get_project_nodes", &GraphEngine::get_project_nodes, py::arg("project_path_substring"))
        .def("get_top_level_project_nodes", &GraphEngine::get_top_level_project_nodes, py::arg("project_path_substring"))
        .def("get_relations", &GraphEngine::get_relations, py::arg("node_id"), py::arg("depth"), py::arg("direction") = 0);
}
