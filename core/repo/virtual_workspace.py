"""
Virtual workspace for repo-native transformations.

Provides an in-memory filesystem abstraction that caches remote repository files,
enabling fast iteration and diffing without local clones.
"""

from typing import Dict, Optional, Set, List
from dataclasses import dataclass, field
from pathlib import Path
import difflib

from .base import RepoConnector, RepoFile


@dataclass
class VirtualFile:
    """Represents a file in the virtual workspace."""
    path: str
    content: str
    sha: Optional[str] = None
    is_modified: bool = False
    is_new: bool = False
    original_content: Optional[str] = None


class VirtualRepo:
    """
    Virtual repository workspace for in-memory file operations.
    
    Features:
    - Lazy loading from remote repo
    - In-memory caching
    - Change tracking
    - Diff generation
    - Zero disk dependency
    """
    
    def __init__(self, connector: RepoConnector, ref: Optional[str] = None):
        """
        Initialize virtual workspace.
        
        Args:
            connector: Repository connector (GitHub, GitLab, etc.)
            ref: Branch/commit reference to use
        """
        self.connector = connector
        self.ref = ref or connector.base_branch
        self._cache: Dict[str, VirtualFile] = {}
        self._loaded_paths: Set[str] = set()
    
    def read(self, path: str) -> str:
        """
        Read file content (from cache or remote).
        
        Args:
            path: File path
            
        Returns:
            File content as string
        """
        if path in self._cache:
            return self._cache[path].content
        
        # Load from remote
        content = self.connector.read_file(path, ref=self.ref)
        self._cache[path] = VirtualFile(
            path=path,
            content=content,
            original_content=content,
            is_new=False
        )
        self._loaded_paths.add(path)
        
        return content
    
    def write(self, path: str, content: str):
        """
        Write file content to virtual workspace.
        
        Args:
            path: File path
            content: New file content
        """
        if path in self._cache:
            # Update existing file
            vfile = self._cache[path]
            if vfile.original_content is None:
                vfile.original_content = vfile.content
            vfile.content = content
            vfile.is_modified = (content != vfile.original_content)
        else:
            # New file
            self._cache[path] = VirtualFile(
                path=path,
                content=content,
                is_new=True,
                is_modified=True,
                original_content=None
            )
    
    def exists(self, path: str) -> bool:
        """
        Check if file exists in virtual workspace or remote.
        
        Args:
            path: File path
            
        Returns:
            True if file exists
        """
        if path in self._cache:
            return not self._cache[path].is_new or self._cache[path].content != ""
        
        return self.connector.file_exists(path, ref=self.ref)
    
    def delete(self, path: str):
        """
        Mark file for deletion.
        
        Args:
            path: File path
        """
        if path in self._cache:
            vfile = self._cache[path]
            if vfile.is_new:
                # Remove new file that hasn't been committed
                del self._cache[path]
            else:
                # Mark existing file for deletion
                vfile.content = ""
                vfile.is_modified = True
        else:
            # Load file and mark for deletion
            if self.connector.file_exists(path, ref=self.ref):
                self._cache[path] = VirtualFile(
                    path=path,
                    content="",
                    original_content=self.connector.read_file(path, ref=self.ref),
                    is_modified=True,
                    is_new=False
                )
    
    def list_files(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all files in virtual workspace.
        
        Args:
            pattern: Optional glob pattern to filter files
            
        Returns:
            List of file paths
        """
        import fnmatch
        
        # Get files from cache
        cached_files = set(self._cache.keys())
        
        # Get files from remote (lazy load)
        remote_files = set(self.connector.get_file_tree(ref=self.ref))
        
        all_files = cached_files | remote_files
        
        if pattern:
            all_files = {f for f in all_files if fnmatch.fnmatch(f, pattern)}
        
        return sorted(all_files)
    
    def get_changes(self) -> Dict[str, VirtualFile]:
        """
        Get all modified or new files.
        
        Returns:
            Dictionary mapping file paths to VirtualFile objects
        """
        return {
            path: vfile
            for path, vfile in self._cache.items()
            if vfile.is_modified or vfile.is_new
        }
    
    def has_changes(self) -> bool:
        """
        Check if there are any pending changes.
        
        Returns:
            True if there are modified or new files
        """
        return any(vfile.is_modified or vfile.is_new for vfile in self._cache.values())
    
    def get_diff(self, path: str) -> Optional[str]:
        """
        Get unified diff for a specific file.
        
        Args:
            path: File path
            
        Returns:
            Unified diff string or None if no changes
        """
        if path not in self._cache:
            return None
        
        vfile = self._cache[path]
        if not vfile.is_modified and not vfile.is_new:
            return None
        
        original = (vfile.original_content or "").splitlines(keepends=True)
        modified = vfile.content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original,
            modified,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm=""
        )
        
        return "".join(diff)
    
    def get_all_diffs(self) -> str:
        """
        Get unified diffs for all changed files.
        
        Returns:
            Combined unified diff string
        """
        diffs = []
        
        for path in sorted(self._cache.keys()):
            diff = self.get_diff(path)
            if diff:
                diffs.append(diff)
        
        return "\n".join(diffs)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about changes.
        
        Returns:
            Dictionary with counts of modified, new, and deleted files
        """
        stats = {
            'modified': 0,
            'new': 0,
            'deleted': 0,
            'total': 0
        }
        
        for vfile in self._cache.values():
            if vfile.is_new:
                stats['new'] += 1
                stats['total'] += 1
            elif vfile.is_modified:
                if vfile.content == "":
                    stats['deleted'] += 1
                else:
                    stats['modified'] += 1
                stats['total'] += 1
        
        return stats
    
    def commit_changes(self, message: str, branch: Optional[str] = None) -> int:
        """
        Commit all changes to the remote repository.
        
        Args:
            message: Commit message
            branch: Target branch (defaults to connector's base_branch)
            
        Returns:
            Number of files committed
        """
        branch = branch or self.connector.base_branch
        committed = 0
        
        for path, vfile in self.get_changes().items():
            if vfile.content == "" and not vfile.is_new:
                # Delete file
                self.connector.delete_file(path, message, branch)
            else:
                # Create or update file
                self.connector.write_file(path, vfile.content, message, branch)
            
            # Mark as committed
            vfile.is_modified = False
            vfile.is_new = False
            vfile.original_content = vfile.content
            committed += 1
        
        return committed
    
    def export_bundle(self, output_dir: str):
        """
        Export all modified and new files to a local directory.
        
        Args:
            output_dir: Directory to export files to
        """
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for path, vfile in self.get_changes().items():
            if vfile.content == "":
                continue  # Skip deleted files
            
            file_path = output_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(vfile.content, encoding='utf-8')
    
    def reset(self):
        """Reset all changes and clear cache."""
        self._cache.clear()
        self._loaded_paths.clear()
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"VirtualRepo(repo={self.connector.get_repo_url()}, "
            f"ref={self.ref}, changes={stats['total']})"
        )
