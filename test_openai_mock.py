"""Mocked tests for OpenAI integration (0 cost, local development)."""
import os
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv
import pytest

load_dotenv()


@patch('openai.OpenAI')
def test_basic_call_mocked(mock_openai_client):
    """Test basic call with mocked OpenAI response."""
    print(" Testing openAi base connection (MOCKED) ")
    
    # Mock the response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Rocket is ready to gear up!"
    mock_response.usage.total_tokens = 42
    
    # Configure the mock client
    mock_client_instance = Mock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance
    
    # Now run the test
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Drive me by Saying 'Rocket is ready to gear up!'"}
        ],
        max_tokens=50,
    )
    
    message = response.choices[0].message.content
    print(f" OpenAi Response : {message}")
    print(f"Used token count : {response.usage.total_tokens}")
    print(f"Cost : ${(response.usage.total_tokens * 0.01) / 1000:.4f}")
    print(" Boom openAi test successful (MOCKED) ")
    
    assert message == "Rocket is ready to gear up!"
    assert response.usage.total_tokens == 42


@patch('openai.OpenAI')
def test_streaming_mocked(mock_openai_client):
    """Test streaming with mocked OpenAI response."""
    print(" Testing openAi streaming connection (MOCKED) ")
    
    # Mock streaming chunks
    mock_chunks = [
        Mock(choices=[Mock(delta=Mock(content="1\n"))]),
        Mock(choices=[Mock(delta=Mock(content="2\n"))]),
        Mock(choices=[Mock(delta=Mock(content="3\n"))]),
        Mock(choices=[Mock(delta=Mock(content="4\n"))]),
        Mock(choices=[Mock(delta=Mock(content="5"))]),
    ]
    
    # Configure the mock client
    mock_client_instance = Mock()
    mock_client_instance.chat.completions.create.return_value = mock_chunks
    mock_openai_client.return_value = mock_client_instance
    
    # Now run the test
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print(" AI: ", end="", flush=True)
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Count from 1 -- 5  one number per line.."}
        ],
        max_tokens=50,
        stream=True
    )
    
    output = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="", flush=True)
    
    print("\n Boom openAi streaming test successful (MOCKED) ")
    assert "1" in output and "5" in output


if __name__ == "__main__":
    print("=" * 60)
    print(" Open AI integration MOCKED tests! ")
    print("=" * 60)
    
    try:
        test_basic_call_mocked()
        test_streaming_mocked()
        
        print("\n" + "=" * 60)
        print(" ROCKET ~ OpenAI Mocked Tests Successful! ")
        print("=" * 60)
    except Exception as e:
        print(f"\n Error: {e}")
        raise e
