import os
import json
import asyncio
import base64
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMRequest:
    """Standard request format for LLM providers."""
    system_prompt: str
    user_message: str
    images: List[str] = None  # List of image file paths
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class LLMResponse:
    """Standard response format from LLM providers."""
    content: str
    success: bool
    error_message: Optional[str] = None
    usage: Optional[Dict] = None
    raw_response_data: Optional[Dict] = None # Added for comprehensive response data


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation using the new google-genai library."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-pro"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using the new Gemini API."""
        if not self.is_configured():
            return LLMResponse(
                content="",
                success=False,
                error_message="Gemini API key not configured"
            )
        
        try:
            from google import genai
            from google.genai import types
            
            # Create client
            client = genai.Client(api_key=self.api_key)
            
            # Prepare content parts
            content_parts = []
            
            # Add text content
            content_parts.append(types.Part.from_text(text=request.user_message))
            
            # Add images if provided
            if request.images:
                for image_path in request.images:
                    if os.path.exists(image_path):
                        # Read and encode image as base64
                        with open(image_path, 'rb') as f:
                            image_data = f.read()
                        
                        # Determine MIME type based on file extension
                        file_ext = image_path.lower().split('.')[-1]
                        mime_type = f"image/{file_ext}"
                        if file_ext == 'jpg':
                            mime_type = "image/jpeg"
                        
                        print(f"   📸 Adding image: {image_path}")
                        print(f"      Size: {len(image_data)} bytes")
                        print(f"      MIME type: {mime_type}")
                        
                        content_parts.append(
                            types.Part.from_bytes(
                                data=image_data,
                                mime_type=mime_type
                            )
                        )
            
            # Create contents
            contents = [
                types.Content(
                    role="user",
                    parts=content_parts
                )
            ]
            
            # Create generation config
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=-1,  # Enable thinking
                    include_thoughts=True,  # Include thinking in response
                ),
                response_mime_type="text/plain",
                system_instruction=[
                    types.Part.from_text(text=request.system_prompt)
                ],
                max_output_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            
            # For debugging: print the request structure
            print(f"\n🔍 DEBUG: Gemini API Request Structure:")
            print(f"   Model: {self.model}")
            print(f"   System instruction length: {len(request.system_prompt)} chars")
            print(f"   User message length: {len(request.user_message)} chars")
            print(f"   Images provided: {len(request.images) if request.images else 0}")
            print(f"   Max tokens: {request.max_tokens}")
            print(f"   Temperature: {request.temperature}")
            print(f"   Thinking budget: -1 (enabled)")
            
            # Print the actual parameters that will be sent to the API
            print(f"\n📋 API Call Parameters:")
            print(f"   client.models.generate_content(")
            print(f"       model='{self.model}',")
            print(f"       contents=[")
            print(f"           types.Content(")
            print(f"               role='user',")
            print(f"               parts=[")
            for i, part in enumerate(content_parts):
                if hasattr(part, 'text') and part.text:
                    preview = part.text[:100] + "..." if len(part.text) > 100 else part.text
                    print(f"                   types.Part.from_text('{preview}'),")
                elif hasattr(part, 'data') and part.data:
                    mime_type = getattr(part, 'mime_type', 'unknown')
                    data_size = len(part.data) if part.data else 0
                    print(f"                   types.Part.from_bytes(mime_type='{mime_type}', data=<{data_size} bytes>),")
                else:
                    # Try to get more info about the part
                    part_attrs = [attr for attr in dir(part) if not attr.startswith('_')]
                    print(f"                   types.Part(<type: {type(part)}, attrs: {part_attrs}>),")
            print(f"               ]")
            print(f"           )")
            print(f"       ],")
            print(f"       config=types.GenerateContentConfig(")
            print(f"           thinking_config=types.ThinkingConfig(thinking_budget=-1),")
            print(f"           response_mime_type='text/plain',")
            print(f"           system_instruction=[types.Part.from_text(system_prompt)],")
            print(f"           max_output_tokens={request.max_tokens},")
            print(f"           temperature={request.temperature}")
            print(f"       )")
            print(f"   )")
            
            # Generate response
            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            
            print(f"   🔍 Raw response type: {type(response)}")
            print(f"   🔍 Raw response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            
            # Extract comprehensive response data
            response_data = {
                "model": self.model,
                "raw_response_type": str(type(response)),
                "candidates": [],
                "usage_metadata": None,
                "prompt_feedback": None,
                "thinking": None
            }
            
            # Extract usage metadata
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = response.usage_metadata
                response_data["usage_metadata"] = {
                    "prompt_token_count": getattr(usage_metadata, 'prompt_token_count', 0),
                    "candidates_token_count": getattr(usage_metadata, 'candidates_token_count', 0),
                    "total_token_count": getattr(usage_metadata, 'total_token_count', 0),
                }
                print(f"   📊 Token usage: {response_data['usage_metadata']}")
            
            # Extract prompt feedback
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                response_data["prompt_feedback"] = str(response.prompt_feedback)
            
            # Extract candidates and content
            main_content = ""
            thinking_content = ""
            
            if hasattr(response, 'candidates') and response.candidates:
                for i, candidate in enumerate(response.candidates):
                    candidate_data = {
                        "index": i,
                        "finish_reason": getattr(candidate, 'finish_reason', None),
                        "safety_ratings": [],
                        "content_parts": []
                    }
                    
                    # Extract safety ratings
                    if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                        for rating in candidate.safety_ratings:
                            candidate_data["safety_ratings"].append({
                                "category": getattr(rating, 'category', None),
                                "probability": getattr(rating, 'probability', None)
                            })
                    
                    # Extract content parts
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for part in candidate.content.parts:
                                part_data = {"type": "unknown"}
                                
                                if hasattr(part, 'text') and part.text:
                                    text = part.text
                                    part_data = {
                                        "type": "text",
                                        "text": text,
                                        "length": len(text)
                                    }
                                    
                                    # Detect if this text part contains thinking/reasoning
                                    # Look for common thinking patterns in Gemini responses
                                    thinking_indicators = [
                                        "my first thought", "i'm thinking", "let me", "i need to",
                                        "okay, so", "my strategy", "i'll start by", "specifically, i'm thinking",
                                        "first, i need to", "i'm up for it", "i'll use", "it looks like",
                                        "i'm confident", "let's do this", "my plan", "alright,", "initial assessment"
                                    ]
                                    
                                    is_thinking = any(indicator in text.lower() for indicator in thinking_indicators)
                                    
                                    # Check if it contains actual HTML content (starts with it, not just mentions it)
                                    starts_with_html_markdown = text.strip().startswith('```html')
                                    starts_with_doctype = text.strip().startswith('<!DOCTYPE')
                                    starts_with_html_tag = text.strip().startswith('<html')
                                    is_actual_html = starts_with_html_markdown or starts_with_doctype or starts_with_html_tag
                                    
                                    # Classify content with priority: actual HTML > thinking patterns
                                    if is_actual_html and not main_content:
                                        # This is the actual HTML content we want
                                        main_content = text
                                        part_data["is_main_content"] = True
                                        print(f"   📄 Main HTML content identified: {len(text)} chars")
                                    elif is_thinking and not is_actual_html and not thinking_content:
                                        # This is thinking content (and not HTML)
                                        thinking_content = text
                                        part_data["is_thinking"] = True
                                        print(f"   🧠 Thinking content identified: {len(text)} chars")
                                    elif not main_content and not thinking_content:
                                        # Fallback: if nothing identified yet, this might be main content
                                        main_content = text
                                        part_data["is_main_content"] = True
                                        print(f"   📄 Fallback main content: {len(text)} chars")
                                
                                elif hasattr(part, 'thought') and part.thought:
                                    # Dedicated thought part (if available)
                                    part_data = {
                                        "type": "thought",
                                        "thought": part.thought,
                                        "length": len(part.thought)
                                    }
                                    thinking_content = part.thought
                                    print(f"   🧠 Dedicated thinking extracted: {len(part.thought)} chars")
                                
                                candidate_data["content_parts"].append(part_data)
                    
                    response_data["candidates"].append(candidate_data)
            
            # Fallback content extraction if candidates approach didn't work
            if not main_content:
                if hasattr(response, 'text') and response.text:
                    main_content = response.text
                elif hasattr(response, 'content') and response.content:
                    main_content = response.content
            
            # Store thinking content
            if thinking_content:
                response_data["thinking"] = thinking_content
            
            print(f"   🔍 Extracted main content length: {len(main_content) if main_content else 0}")
            if thinking_content:
                print(f"   🧠 Extracted thinking length: {len(thinking_content)}")
            
            # Prepare usage for LLMResponse
            usage = {"prompt_tokens": 0, "completion_tokens": 0}
            if response_data["usage_metadata"]:
                usage = {
                    "prompt_tokens": response_data["usage_metadata"].get("prompt_token_count", 0),
                    "completion_tokens": response_data["usage_metadata"].get("candidates_token_count", 0),
                    "total_tokens": response_data["usage_metadata"].get("total_token_count", 0)
                }
            
            return LLMResponse(
                content=main_content,
                success=True,
                usage=usage,
                raw_response_data=response_data  # Add comprehensive response data
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-vision-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API."""
        if not self.is_configured():
            return LLMResponse(
                content="",
                success=False,
                error_message="OpenAI API key not configured"
            )
        
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": request.system_prompt},
            ]
            
            # Prepare user message content
            user_content = [{"type": "text", "text": request.user_message}]
            
            # Add images if provided
            if request.images:
                for image_path in request.images:
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        # Determine image format
                        image_format = image_path.split('.')[-1].lower()
                        if image_format == 'jpg':
                            image_format = 'jpeg'
                        
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{image_data}"
                            }
                        })
            
            messages.append({"role": "user", "content": user_content})
            
            # Generate response
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                success=True,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        
    def is_configured(self) -> bool:
        return self.api_key is not None
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Claude API."""
        if not self.is_configured():
            return LLMResponse(
                content="",
                success=False,
                error_message="Claude API key not configured"
            )
        
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            # Prepare message content
            content_parts = [{"type": "text", "text": request.user_message}]
            
            # Add images if provided
            if request.images:
                for image_path in request.images:
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        # Determine media type
                        image_format = image_path.split('.')[-1].lower()
                        media_type = f"image/{image_format}"
                        if image_format == 'jpg':
                            media_type = "image/jpeg"
                        
                        content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        })
            
            # Generate response
            response = await client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                messages=[{"role": "user", "content": content_parts}]
            )
            
            return LLMResponse(
                content=response.content[0].text,
                success=True,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens
                }
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e)
            )


class MockProvider(LLMProvider):
    """Mock provider for testing purposes with realistic async timing."""
    
    def __init__(self, mock_response: str = "Mock HTML response"):
        self.mock_response = mock_response
        
    def is_configured(self) -> bool:
        return True
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a mock response for testing with realistic timing simulation."""
        import random
        import time
        
        # Simulate realistic processing time: 2-3 seconds with jitter
        base_time = random.uniform(2.0, 3.0)  # Base 2-3 second range
        jitter = random.uniform(-0.5, 0.5)    # Add ±0.5 second jitter
        processing_time = max(1.0, base_time + jitter)  # Ensure minimum 1 second
        
        print(f"     🧪 Mock provider simulating {processing_time:.1f}s processing...")
        await asyncio.sleep(processing_time)
        
        # Generate a more realistic mock HTML response
        page_info = ""
        if request.images:
            # Extract some info from the request for realism
            page_info = f"<p>📄 Processing page with {len(request.images)} image(s)</p>"
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        mock_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mock Construction Document Page</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f9f9f9;
            line-height: 1.6;
        }}
        .document-header {{ 
            background: #2c5aa0;
            color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        .content-section {{ 
            background: white;
            border: 1px solid #ddd; 
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .technical-specs {{ 
            background: #f0f8ff;
            border-left: 4px solid #2c5aa0;
            padding: 15px;
            margin: 10px 0;
        }}
        .footer {{ 
            font-size: 12px; 
            color: #666; 
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="document-header">
        <h1>🏗️ Construction Document - Mock Page</h1>
        <p>Professional Document Conversion Simulation</p>
    </div>
    
    <div class="content-section">
        <h2>📋 Project Information</h2>
        <p>This is a mock HTML conversion of a construction document page, simulating the output of an AI-powered document processing system.</p>
        {page_info}
        <ul>
            <li><strong>Project Type:</strong> Commercial Construction</li>
            <li><strong>Document Section:</strong> Technical Specifications</li>
            <li><strong>Page Classification:</strong> Detailed Plans</li>
        </ul>
    </div>
    
    <div class="technical-specs">
        <h3>🔧 Technical Specifications</h3>
        <p>Mock technical content that would typically be extracted from construction drawings, including:</p>
        <ul>
            <li>Structural dimensions and measurements</li>
            <li>Material specifications and requirements</li>
            <li>Building codes and compliance notes</li>
            <li>Installation procedures and guidelines</li>
        </ul>
    </div>
    
    <div class="content-section">
        <h3>📐 Drawing Elements</h3>
        <p>This section would contain detailed information about visual elements found in the construction drawing:</p>
        <ul>
            <li>Floor plans and elevation views</li>
            <li>Dimensioning and annotation callouts</li>
            <li>Symbol legends and drawing notes</li>
            <li>Scale references and grid systems</li>
        </ul>
    </div>
    
    <div class="footer">
        <p><strong>🤖 Processing Metadata:</strong></p>
        <ul>
            <li>Provider: Mock LLM (Testing Mode)</li>
            <li>System prompt: {len(request.system_prompt)} characters</li>
            <li>Text content: {len(request.user_message)} characters</li>
            <li>Images processed: {len(request.images) if request.images else 0}</li>
            <li>Processing time: {processing_time:.1f} seconds</li>
            <li>Generated: {timestamp}</li>
        </ul>
    </div>
</body>
</html>"""
        
        return LLMResponse(
            content=mock_html,
            success=True,
            usage={
                "prompt_tokens": random.randint(800, 1200), 
                "completion_tokens": random.randint(1500, 2000)
            }
        )


class LLMInterface:
    """Main interface for interacting with LLM providers."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    async def generate_html_from_page(
        self, 
        system_prompt: str,
        pixmap_path: str,
        text_path: Optional[str] = None,
        page_number: int = 1
    ) -> LLMResponse:
        """
        Generate HTML from page artifacts using the configured LLM provider.
        
        Args:
            system_prompt: The system prompt for HTML generation
            pixmap_path: Path to the page pixmap image
            text_path: Optional path to extracted text
            page_number: Page number for context
            
        Returns:
            LLMResponse containing the generated HTML
        """
        # Build user message with only the extracted text (system prompt provides all instructions)
        user_message = ""
        
        # Add text content if available
        if text_path and os.path.exists(text_path):
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
            if text_content:
                user_message = text_content
        
        # If no text available, provide empty message (image will be primary input)
        if not user_message:
            user_message = ""
        
        # Prepare images
        images = [pixmap_path] if os.path.exists(pixmap_path) else []
        
        # Create request
        request = LLMRequest(
            system_prompt=system_prompt,
            user_message=user_message,
            images=images,
            max_tokens=20000,  # Increased from 8000 to ensure complete HTML
            temperature=0.1
        )
        
        return await self.provider.generate_response(request)
    
    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> LLMProvider:
        """Factory method to create LLM providers."""
        providers = {
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
            "claude": ClaudeProvider,
            "mock": MockProvider
        }
        
        if provider_name not in providers:
            raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")
        
        return providers[provider_name](**kwargs) 