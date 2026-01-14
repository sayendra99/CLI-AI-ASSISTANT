"""Checkpoint 6 Verification Tests for Essential Tools"""

import warnings
warnings.filterwarnings('ignore')

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def run_checks():
    print('=' * 60)
    print('CHECKPOINT 6: Essential Tools Verification')
    print('=' * 60)

    # Check 1: All new tools can be imported
    print()
    print('--- Check 1: All new tools import successfully ---')
    try:
        from Rocket.TOOLS.list_directory import ListDirectoryTool
        from Rocket.TOOLS.search_files import SearchFilesTool
        from Rocket.TOOLS.run_command import RunCommandTool
        print('✓ All new tools import successfully')
    except Exception as e:
        print(f'✗ Import failed: {e}')
        raise

    # Check 2: All 5 tools are registered
    print()
    print('--- Check 2: All 5 tools registered ---')
    try:
        from Rocket.TOOLS.registry import get_registry, reset_registry
        from Rocket.TOOLS.read_file import ReadFileTool
        from Rocket.TOOLS.write_file import WriteFileTool
        
        # Reset and register all tools
        reset_registry()
        registry = get_registry()
        
        registry.register(ReadFileTool(workspace_root=Path('.')))
        registry.register(WriteFileTool(workspace_root=Path('.')))
        registry.register(ListDirectoryTool())
        registry.register(SearchFilesTool())
        registry.register(RunCommandTool())
        
        tools = list(registry._tools.keys())
        
        assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}"
        assert "list_directory" in tools, "list_directory not registered"
        assert "search_files" in tools, "search_files not registered"
        assert "run_command" in tools, "run_command not registered"
        assert "read_file" in tools, "read_file not registered"
        assert "write_file" in tools, "write_file not registered"
        
        print(f'✓ All 5 tools registered: {tools}')
    except Exception as e:
        print(f'✗ Registration check failed: {e}')
        raise

    # Check 3: list_directory works
    print()
    print('--- Check 3: list_directory works ---')
    try:
        tool = registry.get("list_directory")
        result = tool.execute(path=".")
        
        assert result.success, f"list_directory failed: {result.error}"
        assert "count" in result.data, "Missing 'count' in result"
        assert "items" in result.data, "Missing 'items' in result"
        
        print(f"✓ list_directory works - found {result.data['count']} items")
    except Exception as e:
        print(f'✗ list_directory check failed: {e}')
        raise

    # Check 4: search_files works
    print()
    print('--- Check 4: search_files works ---')
    try:
        tool = registry.get("search_files")
        result = tool.execute(pattern="def", path=".", file_pattern="*.py")
        
        assert result.success, f"search_files failed: {result.error}"
        assert "matches" in result.data, "Missing 'matches' in result"
        assert "results" in result.data, "Missing 'results' in result"
        
        print(f"✓ search_files works - found {result.data['matches']} matches")
    except Exception as e:
        print(f'✗ search_files check failed: {e}')
        raise

    # Check 5: run_command works
    print()
    print('--- Check 5: run_command works ---')
    try:
        import sys
        tool = registry.get("run_command")
        
        # Use a platform-appropriate command
        if sys.platform == "win32":
            result = tool.execute(command="cmd /c echo hello")
        else:
            result = tool.execute(command="echo hello")
        
        assert result.success, f"run_command failed: {result.error}"
        assert "stdout" in result.data, "Missing 'stdout' in result"
        assert "hello" in result.data["stdout"].lower(), "Output doesn't contain 'hello'"
        
        print(f"✓ run_command works")
    except Exception as e:
        print(f'✗ run_command check failed: {e}')
        raise

    # Check 6: Tool schemas work
    print()
    print('--- Check 6: Tool schemas generate correctly ---')
    try:
        for tool_name in tools:
            tool = registry.get(tool_name)
            schema = tool.to_gemini_schema()
            
            assert "name" in schema, f"{tool_name}: Schema missing 'name'"
            assert "parameters" in schema, f"{tool_name}: Schema missing 'parameters'"
            
            print(f"  ✓ {tool_name}: schema valid")
        
        print('✓ All tool schemas generate correctly')
    except Exception as e:
        print(f'✗ Schema generation check failed: {e}')
        raise

    # Additional checks for tool properties
    print()
    print('--- Additional: Tool property checks ---')
    try:
        # Check ListDirectoryTool
        ld_tool = registry.get("list_directory")
        assert ld_tool.name == "list_directory"
        assert "list" in ld_tool.description.lower() or "director" in ld_tool.description.lower()
        schema = ld_tool.parameters_schema
        assert "path" in schema["properties"]
        assert "recursive" in schema["properties"]
        assert "path" in schema["required"]
        print("  ✓ ListDirectoryTool properties correct")
        
        # Check SearchFilesTool
        sf_tool = registry.get("search_files")
        assert sf_tool.name == "search_files"
        assert "search" in sf_tool.description.lower() or "pattern" in sf_tool.description.lower()
        schema = sf_tool.parameters_schema
        assert "pattern" in schema["properties"]
        assert "path" in schema["properties"]
        assert "file_pattern" in schema["properties"]
        assert "pattern" in schema["required"]
        print("  ✓ SearchFilesTool properties correct")
        
        # Check RunCommandTool
        rc_tool = registry.get("run_command")
        assert rc_tool.name == "run_command"
        assert "command" in rc_tool.description.lower() or "execute" in rc_tool.description.lower()
        schema = rc_tool.parameters_schema
        assert "command" in schema["properties"]
        assert "cwd" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert "command" in schema["required"]
        print("  ✓ RunCommandTool properties correct")
        
        print('✓ All tool properties correct')
    except Exception as e:
        print(f'✗ Property check failed: {e}')
        raise

    print()
    print('=' * 60)
    print('CHECKPOINT 6: All checks passed! ✓')
    print('=' * 60)
    print()
    print('Summary:')
    print('  - ListDirectoryTool: Lists files/directories with size and type')
    print('  - SearchFilesTool: Grep-like search with regex support')
    print('  - RunCommandTool: Execute shell commands safely')
    print('  - All 5 tools registered and generating valid schemas')
    print()

if __name__ == '__main__':
    run_checks()
