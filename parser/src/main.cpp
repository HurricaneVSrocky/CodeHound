#include <iostream>
#include <clang-c/Index.h>
#include "ast_visitor.h"

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: codegraph-parser <source_file_or_dir> [--update] [--out <file>]" << std::endl;
        return 1;
    }

    std::string file_path = argv[1];
    std::string out_file = "graph_data.bin";

    for (int i = 2; i < argc; ++i) {
        if (std::string(argv[i]) == "--out" && i + 1 < argc) {
            out_file = argv[++i];
        }
    }

    CXIndex index = clang_createIndex(0, 0);

    const char* args[] = {
        "-x", "c++",
        "-std=c++17",
        "-I.",
        "-I..",
    };

    CXTranslationUnit unit = clang_parseTranslationUnit(
        index,
        file_path.c_str(),
        args, sizeof(args) / sizeof(args[0]),
        nullptr, 0,
        CXTranslationUnit_None
    );

    if (unit == nullptr) {
        std::cerr << "Unable to parse translation unit." << std::endl;
        clang_disposeIndex(index);
        return 1;
    }

    // Optional: Print diagnostics for debugging
    unsigned num_diagnostics = clang_getNumDiagnostics(unit);
    for (unsigned i = 0; i < num_diagnostics; ++i) {
        CXDiagnostic diag = clang_getDiagnostic(unit, i);
        CXString diag_str = clang_formatDiagnostic(diag, clang_defaultDiagnosticDisplayOptions());
        std::cout << "Clang Warning/Error: " << clang_getCString(diag_str) << std::endl;
        clang_disposeString(diag_str);
        clang_disposeDiagnostic(diag);
    }

    CXCursor cursor = clang_getTranslationUnitCursor(unit);
    
    ASTVisitor visitor;
    visitor.Visit(cursor);
    visitor.Save(out_file);

    clang_disposeTranslationUnit(unit);
    clang_disposeIndex(index);

    std::cout << "Parse completed: " << out_file << " generated." << std::endl;
    return 0;
}
