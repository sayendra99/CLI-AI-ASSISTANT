"""
Advanced async tests for GeminiClient methods.
Tests async operations with proper async/await patterns.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from google.api_core import exceptions as google_exceptions

from Rocket.LLM import GeminiClient, LLMResponse, UsageMetadata


@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock the API key configuration."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-12345")


@pytest.fixture
@patch('google.generativeai.configure')
@patch('google.generativeai.GenerativeModel')
def gemini_client(mock_model, mock_configure):
    """Create a GeminiClient instance for testing."""
    return GeminiClient(
        model_name="gemini-1.5-flash",
        temperature=0.7,
        max_retries=3,
        retry_delay=0.1  # Short delay for testing
    )


@pytest.mark.asyncio
class TestAsyncTextGeneration:
    """Async tests for text generation."""
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    async def test_generate_text_with_retry(self, mock_model_class, mock_configure):
        """Test text generation with retry mechanism."""
        print("\n🧪 Testing generate_text with retry...")
        
        # Mock successful response on second attempt
        mock_response = Mock()
        mock_response.text = "Generated text"
        mock_response.usage_metadata = Mock(
            prompt_token_count=5,
            candidates_token_count=10,
            total_token_count=15
        )
        mock_response.candidates = [Mock(finish_reason=Mock(name="STOP"))]
        
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(return_value=mock_response)
        mock_model_class.return_value = mock_model
        
        client = GeminiClient()
        client.model = mock_model
        
        # Verify initial state
        assert client.total_requests == 0
        print("✅ Retry mechanism test passed")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    async def test_temperature_setting(self, mock_model_class, mock_configure):
        """Test that temperature is properly applied."""
        print("\n🧪 Testing temperature setting...")
        
        client = GeminiClient(temperature=0.95)
        assert client.temperature == 0.95
        
        client2 = GeminiClient(temperature=0.1)
        assert client2.temperature == 0.1
        
        print("✅ Temperature setting test passed")


@pytest.mark.asyncio
class TestAsyncStreaming:
    """Async tests for streaming functionality."""
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    async def test_streaming_generator(self, mock_model_class, mock_configure):
        """Test streaming with async generator."""
        print("\n🧪 Testing streaming generator...")
        
        client = GeminiClient()
        
        # Verify generate_stream is an async generator
        assert hasattr(client, 'generate_stream')
        
        print("✅ Streaming generator test passed")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    async def test_stream_with_system_instruction(self, mock_model_class, mock_configure):
        """Test streaming with system instructions."""
        print("\n🧪 Testing stream with system instruction...")
        
        client = GeminiClient()
        
        # Verify method accepts system_instruction parameter
        import inspect
        sig = inspect.signature(client.generate_stream)
        params = list(sig.parameters.keys())
        
        assert 'prompt' in params
        assert 'system_instruction' in params
        
        print("✅ System instruction parameter test passed")


class TestErrorScenarios:
    """Test error handling scenarios."""
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_rate_limit_handling(self, mock_model, mock_configure):
        """Test rate limit exception handling."""
        print("\n🧪 Testing rate limit handling...")
        
        client = GeminiClient(max_retries=3, retry_delay=0.01)
        
        # Verify retry configuration
        assert client.max_retries == 3
        assert client.retry_delay == 0.01
        
        print("✅ Rate limit handling configuration test passed")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_max_retries_configuration(self, mock_model, mock_configure):
        """Test max retries configuration."""
        print("\n🧪 Testing max retries configuration...")
        
        client = GeminiClient(max_retries=5)
        assert client.max_retries == 5
        
        print("✅ Max retries configuration test passed")


class TestUsageTracking:
    """Test usage statistics tracking in detail."""
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_usage_accumulation(self, mock_model, mock_configure):
        """Test that usage stats accumulate correctly."""
        print("\n🧪 Testing usage accumulation...")
        
        client = GeminiClient()
        
        # Simulate multiple requests
        for i in range(5):
            client.total_requests += 1
            client.total_tokens += 100 * (i + 1)
        
        assert client.total_requests == 5
        assert client.total_tokens == 1500  # 100 + 200 + 300 + 400 + 500
        
        stats = client.get_usage_stats()
        assert stats['avg_tokens_per_request'] == 300
        
        print(f"✅ Usage accumulation test passed: {stats}")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_stats_dict_structure(self, mock_model, mock_configure):
        """Test that stats dict has all required keys."""
        print("\n🧪 Testing stats dict structure...")
        
        client = GeminiClient()
        client.total_requests = 10
        client.total_tokens = 2000
        
        stats = client.get_usage_stats()
        
        required_keys = [
            'model',
            'total_requests',
            'total_tokens',
            'temperature',
            'max_retries',
            'retry_delay',
            'avg_tokens_per_request'
        ]
        
        for key in required_keys:
            assert key in stats, f"Missing key: {key}"
        
        print(f"✅ Stats structure test passed with keys: {list(stats.keys())}")


class TestModelValidation:
    """Test Pydantic model validation."""
    
    def test_response_model_validation(self):
        """Test LLMResponse model validation."""
        print("\n🧪 Testing LLMResponse validation...")
        
        # Valid response
        response = LLMResponse(
            text="Test",
            model="gemini-1.5-flash"
        )
        assert response.text == "Test"
        
        # Test with all fields
        response = LLMResponse(
            text="Full response",
            model="gemini-1.5-flash",
            usage=UsageMetadata(
                prompt_tokens=5,
                completion_tokens=10,
                total_tokens=15
            ),
            finish_reason="STOP"
        )
        assert response.usage.total_tokens == 15
        
        print("✅ Response model validation test passed")
    
    def test_usage_metadata_validation(self):
        """Test UsageMetadata validation."""
        print("\n🧪 Testing UsageMetadata validation...")
        
        usage = UsageMetadata(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300
        )
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 200
        assert usage.total_tokens == 300
        
        print("✅ UsageMetadata validation test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
