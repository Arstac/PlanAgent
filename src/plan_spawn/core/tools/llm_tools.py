"""
LLM utility tools for agents.
"""
from typing import Dict, Any
from openai import OpenAI
from .registry import register_tool
from ...config.settings import settings


@register_tool(
    name="llm_call",
    description="Make a direct LLM call for text generation, analysis, or transformation. Useful for writing, summarizing, or analyzing content.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt or instruction for the LLM"
            },
            "context": {
                "type": "string",
                "description": "Optional context or input text to process",
                "default": ""
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens in response",
                "default": 2048
            }
        },
        "required": ["prompt"]
    }
)
async def llm_call(
    prompt: str,
    context: str = "",
    max_tokens: int = 2048,
    **kwargs
) -> Dict[str, Any]:
    """
    Make a direct call to Claude for text generation.
    
    Args:
        prompt: The instruction/prompt
        context: Optional context
        max_tokens: Max response length
        
    Returns:
        Dict with generated text
    """
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )

        text = response.choices[0].message.content

        return {
            "status": "success",
            "text": text,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@register_tool(
    name="quality_check",
    description="Check quality of written content (grammar, clarity, coherence). Returns quality score and suggestions.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to check"
            },
            "criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Quality criteria to check (e.g., grammar, clarity, coherence)",
                "default": ["grammar", "clarity", "coherence"]
            }
        },
        "required": ["text"]
    }
)
async def quality_check(
    text: str,
    criteria: list[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Check quality of text content.
    
    Args:
        text: Text to check
        criteria: Quality criteria
        
    Returns:
        Dict with quality assessment
    """
    if criteria is None:
        criteria = ["grammar", "clarity", "coherence", "style"]
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = f"""Analyze the following text for quality based on these criteria: {', '.join(criteria)}.

Provide:
1. Overall quality score (0-10)
2. Assessment for each criterion (0-10)
3. Specific issues found
4. Suggestions for improvement

Text to analyze:
{text}

Respond in JSON format:
{{
  "overall_score": <number>,
  "criteria_scores": {{"criterion": <number>, ...}},
  "issues": ["issue1", "issue2", ...],
  "suggestions": ["suggestion1", "suggestion2", ...]
}}"""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse JSON response
        import json
        content = response.choices[0].message.content.strip()

        # Clean markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Find JSON object in the text
        json_start = content.find('{')
        if json_start != -1:
            content = content[json_start:]

        try:
            result = json.loads(content)
            result["status"] = "success"
            return result
        except json.JSONDecodeError as je:
            # If JSON parsing fails, return the raw text with error
            return {
                "status": "error",
                "error": f"Failed to parse JSON: {str(je)}",
                "raw_response": content[:500]  # Include snippet of response
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@register_tool(
    name="fact_verify",
    description="Verify factual claims in text. Useful for fact-checking articles.",
    parameters={
        "type": "object",
        "properties": {
            "claim": {
                "type": "string",
                "description": "Factual claim to verify"
            },
            "context": {
                "type": "string",
                "description": "Optional context around the claim",
                "default": ""
            }
        },
        "required": ["claim"]
    }
)
async def fact_verify(
    claim: str,
    context: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    Verify a factual claim.
    Note: This is a simplified version. In production, integrate with
    fact-checking APIs or databases.
    
    Args:
        claim: The claim to verify
        context: Optional context
        
    Returns:
        Dict with verification result
    """
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = f"""Analyze this factual claim and assess its verifiability:

Claim: {claim}
{"Context: " + context if context else ""}

Provide:
1. Verifiability assessment (verifiable/partially-verifiable/not-verifiable)
2. Confidence level (high/medium/low)
3. What would be needed to verify this claim
4. Any obvious red flags

Respond in JSON:
{{
  "verifiable": "<status>",
  "confidence": "<level>",
  "reasoning": "<explanation>",
  "verification_needed": ["source1", "source2", ...],
  "red_flags": ["flag1", ...]
}}"""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=512,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        import json
        content = response.choices[0].message.content.strip()

        # Clean markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Find JSON object in the text
        json_start = content.find('{')
        if json_start != -1:
            content = content[json_start:]

        try:
            result = json.loads(content)
            result["status"] = "success"
            result["claim"] = claim
            return result
        except json.JSONDecodeError as je:
            # If JSON parsing fails, return the raw text with error
            return {
                "status": "error",
                "error": f"Failed to parse JSON: {str(je)}",
                "claim": claim,
                "raw_response": content[:500]  # Include snippet of response
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "claim": claim
        }
