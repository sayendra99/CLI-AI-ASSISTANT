""" Git operations manager.
handles all git interactions: branching, committing , status checks."""

import subprocess
from typing import Optional,List
from pathlib import Path
from dataclasses import dataclass
from Rocket.Utils.logger import get_logger
logger = get_logger(__name__)


@dataclass
class GitStatus:
    """Current git repository status."""
    is_repo: bool
    current_branch: str
    is_clean: bool
    uncommitted_files: List[str]
    is_production_branch: bool


class GitError(Exception):
    """Git operation error."""
    pass


@dataclass
class GitManager:
    """Manages Git operations for Rocket AI Assistant.
    
    Handles:
    - Repository detection
    - Branch operations
    - Commit operations
    - Safety checks
    """
    repo_path: Path
    
    PRODUCTION_BRANCHES = ['main', 'master', 'production', 'prod', 'release']
    
    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize git manager.
        
        Args:
            repo_path: Path to git repository (default: current directory)
        """
        self.repo_path = repo_path or Path.cwd()
        logger.debug(f"GitManager initialized at: {self.repo_path}")
    
    def get_status(self) -> GitStatus:
        """Get current git repository status.
        
        Returns:
            GitStatus object with repository information
        """
        # Check if git repo
        is_repo = self._is_git_repo()
        
        if not is_repo:
            return GitStatus(
                is_repo=False,
                current_branch="",
                is_clean=True,
                uncommitted_files=[],
                is_production_branch=False
            )
        
        # Get current branch
        current_branch = self._get_current_branch()
        
        # Check if clean
        is_clean = self._is_working_tree_clean()
        
        # Get uncommitted files
        uncommitted_files = self._get_uncommitted_files()
        
        # Check if production branch
        is_production = current_branch in self.PRODUCTION_BRANCHES
        
        return GitStatus(
            is_repo=True,
            current_branch=current_branch,
            is_clean=is_clean,
            uncommitted_files=uncommitted_files,
            is_production_branch=is_production
        )
    
    def create_branch(self, branch_name: str, base_branch: Optional[str] = None) -> str:
        """Create and checkout new branch.
        
        Args:
            branch_name: Name for new branch
            base_branch: Branch to create from (default: current branch)
        
        Returns:
            Name of created branch
        
        Raises:
            GitError: If branch creation fails
        """
        try:
            # Check if branch exists
            if self._branch_exists(branch_name):
                # Generate unique name
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                branch_name = f"{branch_name}-{timestamp}"
                logger.warning(f"Branch exists, using: {branch_name}")
            
            # Create and checkout branch
            if base_branch:
                cmd = ['git', 'checkout', '-b', branch_name, base_branch]
            else:
                cmd = ['git', 'checkout', '-b', branch_name]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Created branch: {branch_name}")
            return branch_name
        
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to create branch: {e.stderr.strip()}")from e
        