#!/usr/bin/env python3
"""
Integration Tests for Rocket CLI Performance and Auto-Setup Features

Tests:
1. Performance benchmarks
2. LRU cache effectiveness
3. System capability detection
4. Model recommendation logic
5. Ollama installer functionality
6. Provider selection logic

Author: Rocket AI Team
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPerformanceOptimizations:
    """Test performance optimization features"""
    
    def test_lru_cache_basic_functionality(self):
        """Test that LRU cache actually caches results"""
        from functools import lru_cache
        
        call_count = 0
        
        @lru_cache(maxsize=128)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call with same argument (should use cache)
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different argument (should call function)
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2
    
    def test_agent_executor_caching(self):
        """Test that ToolExecutor caches permission checks"""
        from Rocket.AGENT.Executor import ToolExecutor
        from Rocket.AGENT.Context import ExecutionContext
        from Rocket.MODES.Read_mode import ReadMode
        
        mode = ReadMode()
        context = ExecutionContext(user_prompt="test", mode_name="READ")
        executor = ToolExecutor(mode=mode, context=context)
        
        # Cache info should show hits after repeated calls
        tool_name = "read_file"
        
        # First call
        result1 = executor.is_tool_allowed(tool_name)
        assert result1 is True
        
        # Second call (should hit cache)
        result2 = executor.is_tool_allowed(tool_name)
        assert result2 is True
        
        # Cache should have reduced calls
        cache_info = executor.is_tool_allowed.cache_info()
        assert cache_info.hits > 0


class TestSystemDetection:
    """Test system capability detection"""
    
    def test_system_detector_initialization(self):
        """Test SystemDetector can be initialized"""
        from Rocket.Utils.ollama_auto_setup import SystemDetector
        
        detector = SystemDetector()
        assert detector.os_type in ["Windows", "Linux", "Darwin"]
        assert detector.architecture in ["x86_64", "AMD64", "arm64", "aarch64"]
    
    @patch('psutil.cpu_count')
    def test_cpu_detection(self, mock_cpu_count):
        """Test CPU detection logic"""
        from Rocket.Utils.ollama_auto_setup import SystemDetector
        
        # Mock CPU counts
        mock_cpu_count.side_effect = [8, 16]  # physical, logical
        
        detector = SystemDetector()
        physical, logical, brand = detector._detect_cpu()
        
        assert physical == 8
        assert logical == 16
        assert isinstance(brand, str)
    
    @patch('psutil.virtual_memory')
    def test_ram_detection(self, mock_memory):
        """Test RAM detection"""
        from Rocket.Utils.ollama_auto_setup import SystemDetector
        
        # Mock 16GB total, 8GB available
        mock_mem = Mock()
        mock_mem.total = 16 * 1024 ** 3
        mock_mem.available = 8 * 1024 ** 3
        mock_memory.return_value = mock_mem
        
        detector = SystemDetector()
        total, available = detector._detect_ram()
        
        assert abs(total - 16.0) < 0.1
        assert abs(available - 8.0) < 0.1
    
    def test_system_capabilities_string_representation(self):
        """Test SystemCapabilities string output"""
        from Rocket.Utils.ollama_auto_setup import SystemCapabilities
        
        caps = SystemCapabilities(
            cpu_count_physical=8,
            cpu_count_logical=16,
            cpu_brand="Test CPU",
            ram_total_gb=16.0,
            ram_available_gb=8.0,
            has_gpu=True,
            gpu_name="Test GPU",
            gpu_vram_gb=8.0,
            gpu_vendor="nvidia",
            os_type="Linux",
            architecture="x86_64"
        )
        
        output = str(caps)
        assert "8 cores" in output
        assert "16 threads" in output
        assert "16.0 GB" in output
        assert "Test GPU" in output


class TestModelRecommendation:
    """Test model recommendation logic"""
    
    def test_model_recommender_tiny_system(self):
        """Test recommendation for low-end system"""
        from Rocket.Utils.ollama_auto_setup import (
            ModelRecommender,
            SystemCapabilities,
            ModelSize
        )
        
        # Low-end system: 4GB RAM, no GPU
        caps = SystemCapabilities(
            cpu_count_physical=2,
            cpu_count_logical=4,
            cpu_brand="Low-end CPU",
            ram_total_gb=4.0,
            ram_available_gb=3.0,
            has_gpu=False,
            os_type="Windows",
            architecture="x86_64"
        )
        
        recommender = ModelRecommender()
        recommendation = recommender.recommend(caps)
        
        assert recommendation.model_size == ModelSize.TINY
        assert "1.5b" in recommendation.model_name.lower()
    
    def test_model_recommender_high_end_system(self):
        """Test recommendation for high-end system"""
        from Rocket.Utils.ollama_auto_setup import (
            ModelRecommender,
            SystemCapabilities,
            ModelSize
        )
        
        # High-end system: 64GB RAM, powerful GPU
        caps = SystemCapabilities(
            cpu_count_physical=16,
            cpu_count_logical=32,
            cpu_brand="High-end CPU",
            ram_total_gb=64.0,
            ram_available_gb=48.0,
            has_gpu=True,
            gpu_name="NVIDIA RTX 4090",
            gpu_vram_gb=24.0,
            gpu_vendor="nvidia",
            os_type="Linux",
            architecture="x86_64"
        )
        
        recommender = ModelRecommender()
        recommendation = recommender.recommend(caps)
        
        # Should recommend large or xlarge model
        assert recommendation.model_size in [ModelSize.LARGE, ModelSize.XLARGE]
    
    def test_fallback_models(self):
        """Test fallback model generation"""
        from Rocket.Utils.ollama_auto_setup import (
            ModelRecommender,
            SystemCapabilities
        )
        
        caps = SystemCapabilities(
            cpu_count_physical=8,
            cpu_count_logical=16,
            cpu_brand="Mid CPU",
            ram_total_gb=16.0,
            ram_available_gb=12.0,
            has_gpu=False,
            os_type="Linux",
            architecture="x86_64"
        )
        
        recommender = ModelRecommender()
        fallbacks = recommender.get_fallback_models(caps)
        
        # Should have primary + fallback options
        assert len(fallbacks) >= 2
        # First should be the primary recommendation
        assert fallbacks[0].model_size.value >= fallbacks[1].model_size.value


class TestOllamaInstaller:
    """Test Ollama installer functionality"""
    
    @patch('subprocess.run')
    def test_is_ollama_installed_true(self, mock_run):
        """Test Ollama installation check when installed"""
        from Rocket.Utils.ollama_auto_setup import OllamaInstaller
        
        mock_run.return_value.returncode = 0
        
        installer = OllamaInstaller()
        assert installer.is_ollama_installed() is True
    
    @patch('subprocess.run', side_effect=FileNotFoundError)
    def test_is_ollama_installed_false(self, mock_run):
        """Test Ollama installation check when not installed"""
        from Rocket.Utils.ollama_auto_setup import OllamaInstaller
        
        installer = OllamaInstaller()
        assert installer.is_ollama_installed() is False
    
    @patch('subprocess.run')
    def test_list_installed_models(self, mock_run):
        """Test listing installed models"""
        from Rocket.Utils.ollama_auto_setup import OllamaInstaller
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """NAME                     ID              SIZE
qwen2.5-coder:1.5b       abc123          900MB
codellama:7b            def456          3.8GB
"""
        
        installer = OllamaInstaller()
        models = installer.list_installed_models()
        
        assert "qwen2.5-coder:1.5b" in models
        assert "codellama:7b" in models
        assert len(models) == 2


class TestProviderSelector:
    """Test intelligent provider selection"""
    
    def test_provider_selector_initialization(self):
        """Test ProviderSelector can be initialized"""
        from Rocket.Utils.smart_config import ProviderSelector
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            selector = ProviderSelector(config_path=config_path)
            
            assert selector.config_path == config_path
            assert selector.detector is not None
            assert selector.recommender is not None
    
    def test_gemini_check_with_env_var(self):
        """Test Gemini API key detection from environment"""
        from Rocket.Utils.smart_config import ProviderSelector
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_12345"}):
            selector = ProviderSelector()
            config = selector._check_gemini()
            
            assert config is not None
            assert config["provider"] == "gemini"
            assert config["api_key"] == "test_api_key_12345"
            assert config["source"] == "environment"
    
    def test_gemini_check_from_config_file(self):
        """Test Gemini API key detection from config file"""
        from Rocket.Utils.smart_config import ProviderSelector
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            
            # Create config file with API key
            config_data = {
                "gemini_api_key": "file_api_key_67890",
                "gemini_model": "gemini-pro"
            }
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            selector = ProviderSelector(config_path=config_path)
            config = selector._check_gemini()
            
            assert config is not None
            assert config["provider"] == "gemini"
            assert config["api_key"] == "file_api_key_67890"
            assert config["model"] == "gemini-pro"
            assert config["source"] == "config"
    
    @patch('Rocket.Utils.smart_config.OllamaInstaller.is_ollama_installed')
    def test_detect_best_provider_no_ollama_no_gemini(self, mock_ollama):
        """Test provider detection when nothing is configured"""
        from Rocket.Utils.smart_config import ProviderSelector
        
        mock_ollama.return_value = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            selector = ProviderSelector(config_path=config_path)
            
            provider_type, config = selector.detect_best_provider()
            
            # Should fall back to proxy
            assert provider_type == "proxy"
            assert config["provider"] == "community_proxy"


class TestDataStructurePerformance:
    """Test efficient data structure usage"""
    
    def test_set_vs_list_lookup_performance(self):
        """Test that set lookups are faster than list lookups"""
        import time
        
        items_list = list(range(1000))
        items_set = set(range(1000))
        
        lookups = [100, 500, 999]
        iterations = 10000
        
        # List lookup
        start = time.perf_counter()
        for _ in range(iterations):
            for item in lookups:
                _ = item in items_list
        list_time = time.perf_counter() - start
        
        # Set lookup
        start = time.perf_counter()
        for _ in range(iterations):
            for item in lookups:
                _ = item in items_set
        set_time = time.perf_counter() - start
        
        # Set should be significantly faster
        assert set_time < list_time
        speedup = list_time / set_time
        assert speedup > 5, f"Expected >5x speedup, got {speedup:.1f}x"


class TestGitManagerCaching:
    """Test Git manager caching optimizations"""
    
    def test_git_manager_branch_check_caching(self):
        """Test that Git manager caches branch existence checks"""
        from Rocket.GIT.manager import GitManager
        
        # This test requires a git repository
        # We'll just verify the method has caching enabled
        manager = GitManager()
        
        # Check that _branch_exists has cache
        assert hasattr(manager._branch_exists, 'cache_info')
        
        # Verify cache_info works
        cache_info = manager._branch_exists.cache_info()
        assert hasattr(cache_info, 'hits')
        assert hasattr(cache_info, 'misses')


class TestModeRegistryCaching:
    """Test mode registry caching"""
    
    def test_mode_registry_has_caching(self):
        """Test that mode registry methods are cached"""
        from Rocket.MODES.Register import ModeRegistry
        
        registry = ModeRegistry()
        
        # Verify caching is enabled
        assert hasattr(registry.get, 'cache_info')
        assert hasattr(registry.get_or_default, 'cache_info')
        assert hasattr(registry.list_all, 'cache_info')


def test_import_all_modules():
    """Smoke test: ensure all new modules can be imported"""
    try:
        from Rocket.Utils import ollama_auto_setup
        from Rocket.Utils import smart_config
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
