"""
Tests for the MODES module.

Tests mode registry, mode selection, and individual mode configurations.
"""

import pytest
from Rocket.MODES.Base import BaseMode, ModeConfig
from Rocket.MODES.Register import ModeRegistry, ModeRegistryError
from Rocket.MODES.Read_mode import ReadMode
from Rocket.MODES.Debug_mode import DebugMode
from Rocket.MODES.Think_mode import ThinkMode
from Rocket.MODES.Agent_mode import AgentMode
from Rocket.MODES.Enhancement_mode import EnhanceMode
from Rocket.MODES.Analyze_mode import AnalyzeMode


class TestModeConfig:
    """Test ModeConfig dataclass."""
    
    def test_valid_config(self):
        """Test creating valid configuration."""
        config = ModeConfig(
            name="TEST",
            description="Test mode",
            temperature=0.5,
            max_tokens=1000,
            tools_allowed=["read_file"],
            requires_git_branch=False,
            system_prompt="Test prompt",
            icon="🧪"
        )
        
        assert config.name == "TEST"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
    
    def test_invalid_temperature_high(self):
        """Test temperature validation - too high."""
        with pytest.raises(ValueError, match="Temperature must be 0.0-1.0"):
            ModeConfig(
                name="TEST",
                description="Test",
                temperature=1.5,
                max_tokens=1000
            )
    
    def test_invalid_temperature_low(self):
        """Test temperature validation - too low."""
        with pytest.raises(ValueError, match="Temperature must be 0.0-1.0"):
            ModeConfig(
                name="TEST",
                description="Test",
                temperature=-0.1,
                max_tokens=1000
            )
    
    def test_invalid_max_tokens(self):
        """Test max_tokens validation."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            ModeConfig(
                name="TEST",
                description="Test",
                temperature=0.5,
                max_tokens=0
            )
    
    def test_empty_name(self):
        """Test empty name validation."""
        with pytest.raises(ValueError, match="Mode name cannot be empty"):
            ModeConfig(
                name="",
                description="Test",
                temperature=0.5,
                max_tokens=1000
            )


class TestModeRegistry:
    """Test ModeRegistry class."""
    
    def test_registry_initialization(self):
        """Test creating empty registry."""
        registry = ModeRegistry()
        assert registry.count() == 0
        assert len(registry) == 0
    
    def test_register_mode(self):
        """Test registering a mode."""
        registry = ModeRegistry()
        mode = ReadMode()
        
        registry.register(mode)
        
        assert registry.count() == 1
        assert "READ" in registry
        assert registry.exists("READ")
    
    def test_register_duplicate_mode(self):
        """Test registering duplicate mode raises error."""
        registry = ModeRegistry()
        mode1 = ReadMode()
        mode2 = ReadMode()
        
        registry.register(mode1)
        
        with pytest.raises(ModeRegistryError, match="already registered"):
            registry.register(mode2)
    
    def test_get_existing_mode(self):
        """Test retrieving existing mode."""
        registry = ModeRegistry()
        mode = ReadMode()
        registry.register(mode)
        
        retrieved = registry.get("READ")
        
        assert retrieved is mode
        assert retrieved.config.name == "READ"
    
    def test_get_nonexistent_mode(self):
        """Test retrieving non-existent mode returns None."""
        registry = ModeRegistry()
        
        result = registry.get("NONEXISTENT")
        
        assert result is None
    
    def test_get_case_insensitive(self):
        """Test mode retrieval is case-insensitive."""
        registry = ModeRegistry()
        mode = ReadMode()
        registry.register(mode)
        
        assert registry.get("read") is mode
        assert registry.get("READ") is mode
        assert registry.get("Read") is mode
    
    def test_get_or_default(self):
        """Test get_or_default with existing mode."""
        registry = ModeRegistry()
        read_mode = ReadMode()
        debug_mode = DebugMode()
        registry.register(read_mode)
        registry.register(debug_mode)
        
        result = registry.get_or_default("DEBUG", "READ")
        
        assert result is debug_mode
    
    def test_get_or_default_fallback(self):
        """Test get_or_default falls back to default."""
        registry = ModeRegistry()
        read_mode = ReadMode()
        registry.register(read_mode)
        
        result = registry.get_or_default("NONEXISTENT", "READ")
        
        assert result is read_mode
    
    def test_get_or_default_both_missing(self):
        """Test get_or_default raises when both missing."""
        registry = ModeRegistry()
        
        with pytest.raises(ModeRegistryError, match="Neither"):
            registry.get_or_default("NONEXISTENT", "ALSO_MISSING")
    
    def test_list_all_modes(self):
        """Test listing all modes."""
        registry = ModeRegistry()
        read_mode = ReadMode()
        debug_mode = DebugMode()
        registry.register(read_mode)
        registry.register(debug_mode)
        
        all_modes = registry.list_all()
        
        assert len(all_modes) == 2
        assert read_mode in all_modes
        assert debug_mode in all_modes
    
    def test_list_names(self):
        """Test listing mode names."""
        registry = ModeRegistry()
        registry.register(ReadMode())
        registry.register(DebugMode())
        
        names = registry.list_names()
        
        assert len(names) == 2
        assert "READ" in names
        assert "DEBUG" in names
    
    def test_contains_operator(self):
        """Test 'in' operator support."""
        registry = ModeRegistry()
        registry.register(ReadMode())
        
        assert "READ" in registry
        assert "NONEXISTENT" not in registry
    
    def test_string_representation(self):
        """Test string representation."""
        registry = ModeRegistry()
        registry.register(ReadMode())
        registry.register(DebugMode())
        
        str_repr = str(registry)
        
        assert "ModeRegistry" in str_repr
        assert "2 modes" in str_repr


class TestIndividualModes:
    """Test individual mode configurations."""
    
    def test_read_mode(self):
        """Test READ mode configuration."""
        mode = ReadMode()
        
        assert mode.config.name == "READ"
        assert mode.config.temperature == 0.3
        assert mode.config.requires_git_branch is False
        assert "read_file" in mode.config.tools_allowed
        assert mode.is_tool_allowed("read_file")
    
    def test_debug_mode(self):
        """Test DEBUG mode configuration."""
        mode = DebugMode()
        
        assert mode.config.name == "DEBUG"
        assert mode.config.temperature == 0.4
        assert mode.config.requires_git_branch is False
        assert mode.is_tool_allowed("run_in_terminal")
    
    def test_think_mode(self):
        """Test THINK mode configuration."""
        mode = ThinkMode()
        
        assert mode.config.name == "THINK"
        assert mode.config.temperature == 0.8
        assert mode.config.requires_git_branch is False
        assert len(mode.config.tools_allowed) == 0  # No tools
    
    def test_agent_mode(self):
        """Test AGENT mode configuration."""
        mode = AgentMode()
        
        assert mode.config.name == "AGENT"
        assert mode.config.temperature == 0.6
        assert mode.config.requires_git_branch is True
        assert "ALL" in mode.config.tools_allowed
        assert mode.is_tool_allowed("any_tool")
    
    def test_enhance_mode(self):
        """Test ENHANCE mode configuration."""
        mode = EnhanceMode()
        
        assert mode.config.name == "ENHANCE"
        assert mode.config.temperature == 0.5
        assert mode.config.requires_git_branch is True
        assert mode.is_tool_allowed("edit_file")
    
    def test_analyze_mode(self):
        """Test ANALYZE mode configuration."""
        mode = AnalyzeMode()
        
        assert mode.config.name == "ANALYZE"
        assert mode.config.temperature == 0.5
        assert mode.config.requires_git_branch is False
        assert mode.is_tool_allowed("read_file")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
