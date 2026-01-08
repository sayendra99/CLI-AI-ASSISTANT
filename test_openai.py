"""Tests for the OpenAI integration."""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_basic_call():
    """Test a basic call to the OpenAI API."""
    print(" Testing openAi base connection ")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Drive me by Saying 'Rocket is ready to gear up!'"}
        ],
        max_tokens=50,
    )
    
    message = response.choices[0].message.content
    print(" OpenAi Response : ", {message})
    print(f"Used token count : {response.usage.total_tokens}")
    print(f"Cost : ${(response.usage.total_tokens * 0.01) / 1000:.4f}")
    print(" Boom openAi test successful ")
    
def test_streaming():
    """Test streaming responses from the OpenAI API."""
    print(" Testing openAi streaming connection ")
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
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n Boom openAi streaming test successful ")
    
if __name__ == "__main__":
    print("="* 60)
    print(" Open AI integeration verifired! ")
    print("="* 60)
    
    try:
        test_basic_call()
        test_streaming()
        
        print("\n" + "=" * 60)
        print(" ROCKET ~ OpenAI Integration Test Successful! ")
        print("=" * 60)
    except Exception as e:
        print(f"\n Error:{e}")
        print("\n Verify :")
        print(" 1. OPENAI_API_KEY is correctly set in your environment variables.")
        print(" 2. You have an active internet connection.")
        print(" 3. Your OpenAI API key has sufficient quota.")
        print("Check The openAI Documentation for more details: https://platform.openai.com/docs/api-reference/introduction")
        raise e
    