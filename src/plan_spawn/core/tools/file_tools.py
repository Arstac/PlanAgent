"""
File operation tools for artifact management.
"""
from typing import Dict, Any
from .registry import register_tool


@register_tool(
    name="write_artifact",
    description="Save content as an artifact. Returns the artifact URI for future reference.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Filename for the artifact (e.g., 'research.json', 'article.md')"
            },
            "content": {
                "type": "string",
                "description": "Content to save"
            },
            "content_type": {
                "type": "string",
                "description": "Type of content: text, json, or markdown",
                "enum": ["text", "json", "markdown"],
                "default": "text"
            }
        },
        "required": ["name", "content"]
    }
)
async def write_artifact(
    name: str, 
    content: str, 
    content_type: str = "text",
    step_id: str = None,
    artifact_store = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Write content to an artifact.
    
    Args:
        name: Filename
        content: Content to write
        content_type: Type (text/json/markdown)
        step_id: Current step ID (injected by runtime)
        artifact_store: ArtifactStore instance (injected by runtime)
        
    Returns:
        Dict with artifact URI
    """
    if not artifact_store:
        return {
            "status": "error",
            "error": "ArtifactStore not available"
        }
    
    if not step_id:
        return {
            "status": "error",
            "error": "step_id not provided"
        }
    
    try:
        uri = artifact_store.save(step_id, name, content, content_type)
        return {
            "status": "success",
            "uri": uri,
            "name": name,
            "size": len(content)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@register_tool(
    name="read_artifact",
    description="Read content from an artifact using its URI (artifact://<step_id>/<name>).",
    parameters={
        "type": "object",
        "properties": {
            "uri": {
                "type": "string",
                "description": "Artifact URI (e.g., 'artifact://s1/research.json')"
            }
        },
        "required": ["uri"]
    }
)
async def read_artifact(
    uri: str,
    artifact_store = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Read content from an artifact.
    
    Args:
        uri: Artifact URI
        artifact_store: ArtifactStore instance (injected by runtime)
        
    Returns:
        Dict with artifact content
    """
    if not artifact_store:
        return {
            "status": "error",
            "error": "ArtifactStore not available"
        }
    
    try:
        if not artifact_store.exists(uri):
            return {
                "status": "error",
                "error": f"Artifact not found: {uri}"
            }
        
        content = artifact_store.load(uri)
        metadata = artifact_store.get_metadata(uri)
        
        return {
            "status": "success",
            "uri": uri,
            "content": content,
            "metadata": metadata
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "uri": uri
        }


@register_tool(
    name="list_artifacts",
    description="List all artifacts created in a specific step or in previous steps.",
    parameters={
        "type": "object",
        "properties": {
            "step_id": {
                "type": "string",
                "description": "Step ID to list artifacts from (optional, defaults to current step)"
            }
        },
        "required": []
    }
)
async def list_artifacts(
    step_id: str = None,
    artifact_store = None,
    **kwargs
) -> Dict[str, Any]:
    """
    List artifacts for a step.
    
    Args:
        step_id: Step ID (optional)
        artifact_store: ArtifactStore instance (injected by runtime)
        
    Returns:
        Dict with list of artifact URIs
    """
    if not artifact_store:
        return {
            "status": "error",
            "error": "ArtifactStore not available"
        }
    
    if not step_id:
        # Get from kwargs if injected
        step_id = kwargs.get("current_step_id")
    
    if not step_id:
        return {
            "status": "error",
            "error": "step_id not provided"
        }
    
    try:
        artifacts = artifact_store.list_artifacts(step_id)
        return {
            "status": "success",
            "step_id": step_id,
            "artifacts": artifacts,
            "count": len(artifacts)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
