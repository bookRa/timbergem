#!/usr/bin/env python3
"""
Test script to debug Gemini API setup and see request structure.
"""

import os
import asyncio
from utils.llm_interface import LLMInterface, LLMRequest
from utils.page_to_html_pipeline import PageToHTMLPipeline, PageToHTMLConfig


async def test_gemini_debug():
    """Test Gemini provider with debug output."""
    
    print("🧪 Testing Gemini Provider Debug Output")
    print("=" * 60)
    
    # Check if API key is available
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("   Please set it in backend/.env file")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-10:]}")
    
    # Create Gemini provider
    try:
        provider = LLMInterface.create_provider(
            "gemini",
            api_key=api_key,
            model="gemini-2.5-flash"
        )
        llm_interface = LLMInterface(provider)
        
        print(f"✅ Gemini provider created successfully")
        print(f"   Model: gemini-2.5-flash")
        print(f"   Provider configured: {provider.is_configured()}")
        
    except Exception as e:
        print(f"❌ Error creating Gemini provider: {e}")
        return
    
    # Test with TEST document page 1
    test_pixmap = "../data/processed/TEST/page_1/page_1_pixmap.png"
    test_text = "../data/processed/TEST/page_1/page_1_text.txt"
    
    if not os.path.exists(test_pixmap):
        print(f"❌ Test pixmap not found: {test_pixmap}")
        print("   Please run the pipeline first to generate test artifacts")
        return
    
    if not os.path.exists(test_text):
        print(f"❌ Test text not found: {test_text}")
        print("   Please run the pipeline first to generate test artifacts")
        return
    
    print(f"✅ Test artifacts found:")
    print(f"   Pixmap: {test_pixmap}")
    print(f"   Text: {test_text}")
    
    # Load system prompt
    system_prompt_path = "system_prompts/page_to_html.md"
    if os.path.exists(system_prompt_path):
        with open(system_prompt_path, 'r') as f:
            system_prompt = f.read()
        print(f"✅ System prompt loaded: {len(system_prompt)} characters")
    else:
        system_prompt = "Convert this construction document page to HTML."
        print(f"⚠️  Using default system prompt")
    
    # Create test request
    print(f"\n🔄 Creating test request...")
    
    try:
        # This will call the Gemini provider and show debug output
        response = await llm_interface.generate_html_from_page(
            system_prompt=system_prompt,
            pixmap_path=test_pixmap,
            text_path=test_text,
            page_number=1
        )
        
        print(f"\n🎯 API Response:")
        print(f"   Success: {response.success}")
        if response.success:
            if response.content:
                print(f"   Content length: {len(response.content)} characters")
                print(f"   Content preview: {response.content[:200]}...")
            else:
                print(f"   Content is None - checking raw response")
        else:
            print(f"   Error: {response.error_message}")
            
    except Exception as e:
        print(f"❌ Error during API call: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run the debug test."""
    print("🚀 Starting Gemini API Debug Test")
    print("📋 This will show the exact parameters sent to the API")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the test
    asyncio.run(test_gemini_debug())


if __name__ == "__main__":
    main() 