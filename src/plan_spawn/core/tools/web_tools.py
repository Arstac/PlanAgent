"""
Web-related tools: search and fetch.
"""
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .registry import register_tool
from ...config.settings import settings


@register_tool(
    name="web_search",
    description="Search the web for information. Returns list of search results with titles, URLs, and snippets.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 5
            }
        },
        "required": ["query"]
    }
)
async def web_search(query: str, max_results: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Search the web using Brave Search API (or fallback to DuckDuckGo).
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        Dict with results list
    """
    try:
        # Try Brave Search API if available
        if settings.BRAVE_API_KEY:
            return await _brave_search(query, max_results)
        else:
            # Fallback to simpler search (you can integrate DuckDuckGo or SerpAPI)
            return await _fallback_search(query, max_results)
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "results": []
        }


async def _brave_search(query: str, max_results: int) -> Dict[str, Any]:
    """Search using Brave Search API."""
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": settings.BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": max_results
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                results = []
                
                for item in data.get("web", {}).get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", "")
                    })
                
                return {
                    "status": "success",
                    "query": query,
                    "results": results
                }
            else:
                return {
                    "status": "error",
                    "error": f"API returned status {response.status}",
                    "results": []
                }


async def _fallback_search(query: str, max_results: int) -> Dict[str, Any]:
    """
    Fallback search implementation.
    Returns mock results for development/testing.
    In production, integrate with DuckDuckGo or SerpAPI.
    """
    # Mock results for development
    mock_results = [
        {
            "title": f"Result {i+1} for: {query}",
            "url": f"https://example.com/article-{i+1}",
            "snippet": f"This is a snippet about {query}. Contains relevant information..."
        }
        for i in range(min(3, max_results))
    ]
    
    return {
        "status": "success",
        "query": query,
        "results": mock_results,
        "note": "Using mock results. Configure BRAVE_API_KEY for real search."
    }


@register_tool(
    name="web_fetch",
    description="Fetch and extract text content from a URL. Returns the main text content of the webpage.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            },
            "extract_links": {
                "type": "boolean",
                "description": "Whether to also extract links from the page",
                "default": False
            }
        },
        "required": ["url"]
    }
)
async def web_fetch(url: str, extract_links: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Fetch and extract content from a URL.

    Args:
        url: URL to fetch
        extract_links: Whether to extract links

    Returns:
        Dict with extracted content
    """
    try:
        # Use browser-like headers to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}",
                        "url": url
                    }

                # Try to read with proper encoding detection
                try:
                    # Try UTF-8 first
                    html = await response.text(encoding='utf-8')
                except UnicodeDecodeError:
                    # Fallback to latin-1 which accepts all byte values
                    html = await response.text(encoding='latin-1')
                soup = BeautifulSoup(html, 'lxml')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Extract text
                text = soup.get_text(separator='\n', strip=True)
                
                # Clean up whitespace
                lines = [line.strip() for line in text.splitlines()]
                text = '\n'.join(line for line in lines if line)
                
                # Limit text length (first 10000 chars)
                text = text[:10000]
                
                result = {
                    "status": "success",
                    "url": url,
                    "text": text,
                    "length": len(text)
                }
                
                # Extract links if requested
                if extract_links:
                    links = []
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.startswith('http'):
                            links.append({
                                "text": link.get_text(strip=True),
                                "url": href
                            })
                    result["links"] = links[:20]  # Limit to 20 links
                
                return result
                
    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": "Request timeout",
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "url": url
        }