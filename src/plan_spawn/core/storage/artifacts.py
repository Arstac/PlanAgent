"""
Artifact storage and management.
Handles saving/loading artifacts with logical URIs.
"""
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class ArtifactStore:
    """
    Manages artifact storage with URI-based referencing.
    
    URI format: artifact://<step_id>/<filename>
    Physical path: <base_path>/<step_id>/<filename>
    """
    
    def __init__(self, base_path: str = "./artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create metadata directory
        self.metadata_path = self.base_path / "_metadata"
        self.metadata_path.mkdir(exist_ok=True)
    
    def save(
        self, 
        step_id: str, 
        name: str, 
        content: Any, 
        content_type: str = "text"
    ) -> str:
        """
        Save an artifact and return its URI.
        
        Args:
            step_id: Step identifier
            name: Artifact filename
            content: Content to save
            content_type: One of: text, json, binary
            
        Returns:
            URI in format artifact://<step_id>/<name>
        """
        # Create step directory
        step_dir = self.base_path / step_id
        step_dir.mkdir(exist_ok=True)
        
        file_path = step_dir / name
        
        # Save based on type
        if content_type == "json":
            file_path.write_text(json.dumps(content, indent=2, ensure_ascii=False))
        elif content_type == "binary":
            file_path.write_bytes(content)
        else:  # text
            file_path.write_text(str(content), encoding="utf-8")
        
        # Save metadata
        self._save_metadata(step_id, name, content_type, file_path)
        
        return f"artifact://{step_id}/{name}"
    
    def load(self, uri: str) -> Any:
        """
        Load artifact content from URI.
        
        Args:
            uri: Artifact URI (artifact://<step_id>/<name>)
            
        Returns:
            Artifact content
        """
        step_id, name = self._parse_uri(uri)
        file_path = self.base_path / step_id / name
        
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {uri}")
        
        # Get metadata to determine type
        metadata = self._load_metadata(step_id, name)
        content_type = metadata.get("content_type", "text")
        
        # Load based on type
        if content_type == "json":
            return json.loads(file_path.read_text(encoding="utf-8"))
        elif content_type == "binary":
            return file_path.read_bytes()
        else:
            return file_path.read_text(encoding="utf-8")
    
    def exists(self, uri: str) -> bool:
        """Check if artifact exists."""
        try:
            step_id, name = self._parse_uri(uri)
            file_path = self.base_path / step_id / name
            return file_path.exists()
        except ValueError:
            return False
    
    def list_artifacts(self, step_id: str) -> list[str]:
        """List all artifacts for a step."""
        step_dir = self.base_path / step_id
        if not step_dir.exists():
            return []
        
        return [
            f"artifact://{step_id}/{f.name}" 
            for f in step_dir.iterdir() 
            if f.is_file()
        ]
    
    def get_path(self, uri: str) -> Path:
        """Get physical file path from URI."""
        step_id, name = self._parse_uri(uri)
        return self.base_path / step_id / name
    
    def _parse_uri(self, uri: str) -> tuple[str, str]:
        """Parse artifact URI into (step_id, name)."""
        if not uri.startswith("artifact://"):
            raise ValueError(f"Invalid artifact URI: {uri}")
        
        parts = uri.replace("artifact://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid artifact URI format: {uri}")
        
        return parts[0], parts[1]
    
    def _save_metadata(
        self, 
        step_id: str, 
        name: str, 
        content_type: str,
        file_path: Path
    ):
        """Save artifact metadata."""
        metadata = {
            "step_id": step_id,
            "name": name,
            "content_type": content_type,
            "created_at": datetime.now().isoformat(),
            "size_bytes": file_path.stat().st_size,
            "uri": f"artifact://{step_id}/{name}"
        }
        
        metadata_file = self.metadata_path / f"{step_id}_{name}.meta.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
    
    def _load_metadata(self, step_id: str, name: str) -> dict:
        """Load artifact metadata."""
        metadata_file = self.metadata_path / f"{step_id}_{name}.meta.json"
        if metadata_file.exists():
            return json.loads(metadata_file.read_text())
        return {}
    
    def get_metadata(self, uri: str) -> dict:
        """Get metadata for an artifact."""
        step_id, name = self._parse_uri(uri)
        return self._load_metadata(step_id, name)
    
    def cleanup_step(self, step_id: str):
        """Remove all artifacts for a step."""
        step_dir = self.base_path / step_id
        if step_dir.exists():
            import shutil
            shutil.rmtree(step_dir)
        
        # Cleanup metadata
        for meta_file in self.metadata_path.glob(f"{step_id}_*.meta.json"):
            meta_file.unlink()
