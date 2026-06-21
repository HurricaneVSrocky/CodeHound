import sys
import os
import argparse

# 动态将项目根目录及 backend 目录加入 sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
sys.path.append(os.path.join(ROOT_DIR, 'backend'))

try:
    import agent_tools
except ImportError as e:
    print(f"Error: Failed to import agent_tools from backend: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="CodeHound Graph CLI Tool for AI Agents")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")

    # 'search' 子命令
    search_parser = subparsers.add_parser("search", help="Search code graph node by name")
    search_parser.add_argument("keyword", type=str, help="Search keyword (e.g. function or variable name)")

    # 'relations' 子命令
    relations_parser = subparsers.add_parser("relations", help="Traverse node dependencies and relations")
    relations_parser.add_argument("node_id", type=int, help="Integer Node ID")
    relations_parser.add_argument("--depth", type=int, default=1, help="Hop depth (default: 1)")
    relations_parser.add_argument("--direction", type=int, default=0, help="0=Both, 1=Outgoing (called/read by this), 2=Incoming (calling/reading this)")

    args = parser.parse_args()

    if args.command == "search":
        print(agent_tools.find_node_by_name(args.keyword))
    elif args.command == "relations":
        print(agent_tools.get_node_relations(args.node_id, args.depth, args.direction))

if __name__ == "__main__":
    main()
