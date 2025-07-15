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
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
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
            
            # Extract content from response
            content = ""
            if hasattr(response, 'text') and response.text:
                content = response.text
            elif hasattr(response, 'content') and response.content:
                content = response.content
            elif hasattr(response, 'candidates') and response.candidates:
                # Try to get content from candidates
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        content = candidate.content.parts[0].text
            
            print(f"   🔍 Extracted content length: {len(content) if content else 0}")
            
            return LLMResponse(
                content=content,
                success=True,
                usage={"prompt_tokens": 0, "completion_tokens": 0}  # Gemini doesn't provide detailed usage in new API
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
    """Mock provider for testing purposes."""
    
    def __init__(self, mock_response: str = "Mock HTML response"):
        self.mock_response = mock_response
        
    def is_configured(self) -> bool:
        return True
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a mock response for testing."""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate a simple mock HTML response
        mock_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock Page Conversion</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .mock-content {{ border: 1px solid #ccc; padding: 15px; }}
    </style>
</head>
<body>
    <div class="mock-content">
        <h2>Mock Page Conversion</h2>
        <p>This is a mock response for testing purposes.</p>
        <p>System prompt length: {len(request.system_prompt)} characters</p>
        <p>User message length: {len(request.user_message)} characters</p>
        <p>Images provided: {len(request.images) if request.images else 0}</p>
        <p>Generated at: {asyncio.get_event_loop().time()}</p>
    </div>
</body>
</html>"""
        
        return LLMResponse(
            content=mock_html,
            success=True,
            usage={"prompt_tokens": 100, "completion_tokens": 200}
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
        # Build user message
        user_message_parts = [
            f"Please convert page {page_number} of this construction document into structured HTML."
        ]
        
        # Add text content if available
        if text_path and os.path.exists(text_path):
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
            if text_content:
                user_message_parts.append(f"\n**Extracted Text:**\n{text_content}")
        
        user_message = "\n".join(user_message_parts)
        
        # Prepare images
        images = [pixmap_path] if os.path.exists(pixmap_path) else []
        
        # Create request
        request = LLMRequest(
            system_prompt=system_prompt,
            user_message=user_message,
            images=images,
            max_tokens=8000,  # Increased for HTML output
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