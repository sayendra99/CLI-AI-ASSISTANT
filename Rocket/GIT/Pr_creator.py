import subprocess
from typing import Optional
from dataclasses import dataclass

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


@dataclass
class PRInfo:
    """Pull request information."""
    number: int
    url: str
    title: str
    from_branch: str
    to_branch: str


class PRCreationError(Exception):
    """PR creation failed."""
    pass


class PRCreator:
    """
    Create pull requests automatically.
    
    Supports:
    - GitHub CLI (gh)
    - GitHub API (future)
    - GitLab API (future)
    """
    
    def __init__(self):
        """Initialize PR creator."""
        self.has_gh_cli = self._check_gh_cli()
    
    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is installed."""
        try:
            subprocess.run(
                ['gh', '--version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def create_pr(
        self,
        from_branch: str,
        to_branch: str,
        title: str,
        body: Optional[str] = None,
        draft: bool = False
    ) -> PRInfo:
        """
        Create pull request.
        
        Args:
            from_branch: Source branch
            to_branch: Target branch
            title: PR title
            body: PR description
            draft: Create as draft PR
            
        Returns:
            PRInfo object with PR details
            
        Raises:
            PRCreationError: If PR creation fails
        """
        if self.has_gh_cli:
            return self._create_via_gh_cli(from_branch, to_branch, title, body, draft)
        else:
            raise PRCreationError("No PR creation method available. Install GitHub CLI (gh)")
    
    def _create_via_gh_cli(
        self,
        from_branch: str,
        to_branch: str,
        title: str,
        body: Optional[str],
        draft: bool
    ) -> PRInfo:
        """Create PR using GitHub CLI."""
        try:
            cmd = [
                'gh', 'pr', 'create',
                '--base', to_branch,
                '--head', from_branch,
                '--title', title,
            ]
            
            if body:
                cmd.extend(['--body', body])
            
            if draft:
                cmd.append('--draft')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse PR URL from output
            pr_url = result.stdout.strip()
            
            # Extract PR number from URL
            # Format: https://github.com/user/repo/pull/123
            pr_number = int(pr_url.split('/')[-1])
            
            logger.info(f"Created PR #{pr_number}: {title}")
            
            return PRInfo(
                number=pr_number,
                url=pr_url,
                title=title,
                from_branch=from_branch,
                to_branch=to_branch
            )
            
        except subprocess.CalledProcessError as e:
            raise PRCreationError(f"Failed to create PR: {e.stderr}")
        except (ValueError, IndexError) as e:
            raise PRCreationError(f"Failed to parse PR number from URL: {e}")
