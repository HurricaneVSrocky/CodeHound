#include "ast_visitor.h"
#include <iostream>
#include <fstream>
#include <flatbuffers/flatbuffers.h>

std::string ASTVisitor::GetCursorSpelling(CXCursor cursor) {
    CXString str = clang_getCursorSpelling(cursor);
    std::string result = clang_getCString(str);
    clang_disposeString(str);
    return result;
}

std::string ASTVisitor::GetCursorName(CXCursor cursor) {
    CXString usr = clang_getCursorUSR(cursor);
    std::string result = clang_getCString(usr);
    clang_disposeString(usr);
    if (result.empty()) {
        return GetCursorSpelling(cursor);
    }
    return result;
}

int32_t ASTVisitor::GetOrAddNode(CXCursor cursor) {
    std::string usr = GetCursorName(cursor);
    if (usr.empty()) return 0;
    
    if (usr_to_id.count(usr)) {
        return usr_to_id[usr];
    }
    
    CXSourceLocation loc = clang_getCursorLocation(cursor);
    CXFile file;
    unsigned line, column, offset;
    clang_getSpellingLocation(loc, &file, &line, &column, &offset);
    
    std::string file_path = "";
    if (file) {
        CXString file_name = clang_getFileName(file);
        file_path = clang_getCString(file_name);
        clang_disposeString(file_name);
    }
    
    NodeType type = NodeType_Unknown;
    CXCursorKind kind = clang_getCursorKind(cursor);
    if (kind == CXCursor_ClassDecl) type = NodeType_Class;
    else if (kind == CXCursor_StructDecl) type = NodeType_Struct;
    else if (kind == CXCursor_CXXMethod) type = NodeType_Method;
    else if (kind == CXCursor_FunctionDecl) type = NodeType_Function;
    else if (kind == CXCursor_VarDecl || kind == CXCursor_FieldDecl) type = NodeType_Variable;
    else return 0; // Ignore other types for now
    
    int32_t id = next_id++;
    usr_to_id[usr] = id;
    
    nodes.push_back({id, type, GetCursorSpelling(cursor), file_path, (int32_t)line});
    return id;
}

CXChildVisitResult ASTVisitor::VisitNode(CXCursor cursor, CXCursor parent, CXClientData client_data) {
    ASTVisitor* visitor = static_cast<ASTVisitor*>(client_data);
    CXCursorKind kind = clang_getCursorKind(cursor);

    // Try to register node if it's a declaration
    if (clang_isDeclaration(kind)) {
        visitor->GetOrAddNode(cursor);
    }

    // Call Expression -> Calls edge
    if (kind == CXCursor_CallExpr) {
        CXCursor referenced = clang_getCursorReferenced(cursor);
        int32_t target_id = visitor->GetOrAddNode(referenced);
        
        // Find the function that contains this call
        CXCursor caller = parent;
        while (!clang_isCursorDefinition(caller) && clang_getCursorKind(caller) != CXCursor_TranslationUnit) {
            CXCursorKind p_kind = clang_getCursorKind(caller);
            if (p_kind == CXCursor_FunctionDecl || p_kind == CXCursor_CXXMethod) break;
            caller = clang_getCursorSemanticParent(caller);
            if (clang_Cursor_isNull(caller)) break;
        }
        
        int32_t source_id = visitor->GetOrAddNode(caller);
        if (source_id > 0 && target_id > 0) {
            visitor->edges.push_back({source_id, target_id, EdgeType_Calls});
        }
    }
    // CXXBaseSpecifier -> Inherits edge
    else if (kind == CXCursor_CXXBaseSpecifier) {
        CXCursor referenced = clang_getCursorReferenced(cursor);
        int32_t target_id = visitor->GetOrAddNode(referenced);
        int32_t source_id = visitor->GetOrAddNode(parent);
        if (source_id > 0 && target_id > 0) {
            visitor->edges.push_back({source_id, target_id, EdgeType_Inherits});
        }
    }
    // DeclRefExpr -> Reads/Writes edge (simplified)
    else if (kind == CXCursor_DeclRefExpr) {
        CXCursor referenced = clang_getCursorReferenced(cursor);
        if (clang_getCursorKind(referenced) == CXCursor_VarDecl || clang_getCursorKind(referenced) == CXCursor_FieldDecl) {
            int32_t target_id = visitor->GetOrAddNode(referenced);
            
            CXCursor caller = parent;
            while (clang_getCursorKind(caller) != CXCursor_FunctionDecl && 
                   clang_getCursorKind(caller) != CXCursor_CXXMethod &&
                   clang_getCursorKind(caller) != CXCursor_TranslationUnit) {
                caller = clang_getCursorSemanticParent(caller);
                if (clang_Cursor_isNull(caller)) break;
            }
            int32_t source_id = visitor->GetOrAddNode(caller);
            
            if (source_id > 0 && target_id > 0) {
                // Determine Read vs Write (simplification: if it's LHS of assign, write, else read)
                // For MVP, we just mark as Reads
                visitor->edges.push_back({source_id, target_id, EdgeType_Reads});
            }
        }
    }

    return CXChildVisit_Recurse;
}

void ASTVisitor::Visit(CXCursor root_cursor) {
    clang_visitChildren(root_cursor, VisitNode, this);
}

void ASTVisitor::Save(const std::string& out_path) {
    flatbuffers::FlatBufferBuilder builder(1024);
    
    std::vector<flatbuffers::Offset<Node>> fb_nodes;
    for (const auto& n : nodes) {
        auto name_str = builder.CreateString(n.name);
        auto path_str = builder.CreateString(n.file_path);
        
        NodeBuilder nb(builder);
        nb.add_id(n.id);
        nb.add_type(n.type);
        nb.add_name(name_str);
        nb.add_file_path(path_str);
        nb.add_start_line(n.start_line);
        fb_nodes.push_back(nb.Finish());
    }
    
    std::vector<Edge> fb_edges;
    for (const auto& e : edges) {
        fb_edges.push_back(Edge(e.source_id, e.target_id, e.type));
    }
    
    auto nodes_vec = builder.CreateVector(fb_nodes);
    auto edges_vec = builder.CreateVectorOfStructs(fb_edges);
    
    GraphPayloadBuilder gb(builder);
    gb.add_version(1);
    gb.add_nodes(nodes_vec);
    gb.add_edges(edges_vec);
    auto root = gb.Finish();
    
    builder.Finish(root);
    
    std::ofstream out(out_path, std::ios::binary);
    out.write((const char*)builder.GetBufferPointer(), builder.GetSize());
    out.close();
}
