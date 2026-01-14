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

    # Check 1: All tools can be imported
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
    print('--- Check 2: All 5 tools are registered ---')
    try:
        from Rocket.TOOLS.registry import get_registry, reset_registry
        from Rocket.TOOLS.read_file import ReadFileTool
        from Rocket.TOOLS.write_file import WriteFileTool
        
        # Reset and register all tools
        reset_registry()
        registry = get_registry()
        
        # Register all 5 tools
        registry.register(ReadFileTool(workspace_root=Path('.')))
        registry.register(WriteFileTool(workspace_root=Path('.')))
        registry.register(ListDirectoryTool(workspace_root=Path('.')))
        registry.register(SearchFilesTool(workspace_root=Path('.')))
        registry.register(RunCommandTool(workspace_root=Path('.')))
        
        tools = list(registry._tools.keys())
        
        assert len(tools) == 5, f'Expected 5 tools, got {len(tools)}'
        assert 'list_directory' in tools, 'list_directory not registered'
        assert 'search_files' in tools, 'search_files not registered'
        assert 'run_command' in tools, 'run_command not registered'
        assert 'read_file' in tools, 'read_file not registered'
        assert 'write_file' in tools, 'write_file not registered'
        
        print(f'✓ All 5 tools registered: {tools}')
    except Exception as e:
        print(f'✗ Registration check failed: {e}')
        raise

    # Check 3: List directory works
    print()
    print('--- Check 3: list_directory works ---')
    try:
        tool = registry.get('list_directory')
        result = tool.execute(path='.')
        
        assert result.success, f'list_directory failed: {result.error}'
        assert 'count' in result.data, 'Missing count in output'
        assert 'items' in result.data, 'Missing items in output'
        
        print(f"✓ list_directory works - found {result.data['count']} items")
    except Exception as e:
        print(f'✗ list_directory check failed: {e}')
        raise

    # Check 4: search_files works
    print()
    print('--- Check 4: search_files works ---')
    try:
        tool = registry.get('search_files')
        result = tool.execute(pattern='def', path='.', file_pattern='*.py')
        
        assert result.success, f'search_files failed: {result.error}'
        assert 'matches' in result.data, 'Missing matches in output'
        assert 'results' in result.data, 'Missing results in output'
        
        print(f"✓ search_files works - found {result.data['matches']} matches")
    except Exception as e:
        print(f'✗ search_files check failed: {e}')
        raise

    # Check 5: run_command works
    print()
    print('--- Check 5: run_command works ---')
    try:
        tool = registry.get('run_command')
        
        # Use platform-appropriate echo command
        if sys.platform == 'win32':
            result = tool.execute(command='cmd /c echo hello')
        else:
            result = tool.execute(command='echo hello')
        
        assert result.success, f'run_command failed: {result.error}'
        assert 'stdout' in result.data, 'Missing stdout in output'
        assert 'hello' in result.data['stdout'], f"Expected 'hello' in stdout, got: {result.data['stdout']}"
        
        print('✓ run_command works')
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
            
            assert 'name' in schema, f'{tool_name}: Missing name in schema'
            assert 'parameters' in schema, f'{tool_name}: Missing parameters in schema'
        
        print('✓ All tool schemas generate correctly')
    except Exception as e:
        print(f'✗ Schema generation check failed: {e}')
        raise

    # Summary
    print()
    print('=' * 60)
    print('CHECKPOINT 6: ALL CHECKS PASSED ✓')
    print('=' * 60)
    print()
    print('Summary:')
    print('  - 3 new tools created (list_directory, search_files, run_command)')
    print('  - All 5 tools register and work correctly')
    print('  - LLM schemas generate for all tools')
    print()
    print('Rocket now has essential tools for:')
    print('  📖 read_file - Read file contents')
    print('  ✏️  write_file - Write/modify files')
    print('  📁 list_directory - Explore directory structure')
    print('  🔍 search_files - Search for patterns in code')
    print('  ⚡ run_command - Execute shell commands')

if __name__ == '__main__':
    run_checks()
