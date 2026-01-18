"""
Authentication Module for Rocket CLI

Handles GitHub OAuth device flow authentication, token storage,
and session management.
"""

import json
import time
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import aiohttp

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)

# Auth storage location
AUTH_DIR = Path.home() / ".rocket-cli"
AUTH_FILE = AUTH_DIR / "auth.json"

# Default proxy URL
DEFAULT_PROXY_URL = "https://api.rocket-cli.dev"


@dataclass
class AuthSession:
    """Represents an authenticated session."""
    token: str
    username: str
    name: Optional[str]
    user_id: str
    created_at: str
    expires_at: str


class AuthError(Exception):
    """Authentication error."""
    pass


class AuthManager:
    """Manages authentication for Rocket CLI."""
    
    def __init__(self, proxy_url: str = "https://api.rocket-cli.dev"):
        self.proxy_url = proxy_url.rstrip('/')
        self._session: Optional[AuthSession] = None
    
    @property
    def auth_file(self) -> Path:
        """Path to the auth storage file."""
        config_dir = Path.home() / ".rocket-cli"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "auth.json"
    
    def get_stored_token(self) -> Optional[str]:
        """Get stored authentication token."""
        if not self.auth_file.exists():
            return None
        
        try:
            with open(self.auth_file, 'r') as f:
                data = json.load(f)
                return data.get('token')
        except (json.JSONDecodeError, IOError):
            return None
    
    def store_token(self, token: str, user_data: dict) -> None:
        """Store authentication token and user data."""
        data = {
            'token': token,
            'username': user_data.get('username'),
            'name': user_data.get('name'),
            'user_id': user_data.get('id'),
            'stored_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }
        
        with open(self.auth_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Set restrictive permissions (owner read/write only)
        self.auth_file.chmod(0o600)
    
    def clear_token(self) -> None:
        """Remove stored authentication token."""
        if self.auth_file.exists():
            self.auth_file.unlink()
        self._session = None
    
    def get_stored_session(self) -> Optional[dict]:
        """Get stored session data without validation."""
        if not self.auth_file.exists():
            return None
        
        try:
            with open(self.auth_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    async def validate_token(self, token: str) -> Optional[AuthSession]:
        """Validate token with the server."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.proxy_url}/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    if not data.get('authenticated'):
                        return None
                    
                    user = data.get('user', {})
                    session_data = data.get('session', {})
                    
                    return AuthSession(
                        token=token,
                        username=user.get('username', ''),
                        name=user.get('name'),
                        user_id=user.get('id', ''),
                        created_at=session_data.get('created_at', ''),
                        expires_at=session_data.get('expires_at', ''),
                    )
            except aiohttp.ClientError:
                return None
    
    async def get_current_session(self) -> Optional[AuthSession]:
        """Get current authenticated session, validating if needed."""
        if self._session:
            return self._session
        
        token = self.get_stored_token()
        if not token:
            return None
        
        session = await self.validate_token(token)
        if session:
            self._session = session
        else:
            # Token is invalid, clear it
            self.clear_token()
        
        return session
    
    async def login_device_flow(self, open_browser: bool = True) -> AuthSession:
        """
        Perform GitHub OAuth device flow login.
        
        Args:
            open_browser: Whether to automatically open the verification URL
        
        Returns:
            AuthSession on successful authentication
        
        Raises:
            AuthError on failure
        """
        async with aiohttp.ClientSession() as session:
            # Start device flow
            try:
                async with session.post(
                    f"{self.proxy_url}/api/auth/device"
                ) as response:
                    if response.status != 200:
                        raise AuthError(f"Failed to start login: {response.status}")
                    
                    data = await response.json()
            except aiohttp.ClientError as e:
                raise AuthError(f"Failed to connect to server: {e}")
            
            user_code = data['user_code']
            verification_uri = data['verification_uri']
            device_code = data['device_code']
            expires_in = data['expires_in']
            interval = data.get('interval', 5)
            
            # Show instructions to user
            print()
            print("🔐 GitHub Authentication Required")
            print("=" * 40)
            print()
            print(f"1. Open: {verification_uri}")
            print(f"2. Enter code: {user_code}")
            print()
            
            # Open browser if requested
            if open_browser:
                print("Opening browser...")
                webbrowser.open(verification_uri)
            
            print("Waiting for authorization", end="", flush=True)
            
            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < expires_in:
                await asyncio.sleep(interval)
                print(".", end="", flush=True)
                
                try:
                    async with session.post(
                        f"{self.proxy_url}/api/auth/device/poll",
                        json={"device_code": device_code}
                    ) as response:
                        if response.status != 200:
                            continue
                        
                        result = await response.json()
                        
                        if result['status'] == 'success':
                            print(" ✓")
                            print()
                            
                            # Store token
                            self.store_token(result['token'], result.get('user', {}))
                            
                            # Create session object
                            user = result.get('user', {})
                            auth_session = AuthSession(
                                token=result['token'],
                                username=user.get('username', ''),
                                name=user.get('name'),
                                user_id='',  # Will be filled on validation
                                created_at='',
                                expires_at='',
                            )
                            
                            self._session = auth_session
                            return auth_session
                        
                        elif result['status'] == 'expired':
                            print(" ✗")
                            raise AuthError("Authorization expired. Please try again.")
                        
                        elif result['status'] == 'error':
                            print(" ✗")
                            raise AuthError(f"Authorization failed: {result.get('error', 'Unknown error')}")
                        
                        # status == 'pending', continue polling
                        
                except aiohttp.ClientError:
                    continue
            
            print(" ✗")
            raise AuthError("Authorization timed out. Please try again.")
    
    async def logout(self) -> bool:
        """
        Logout and invalidate the current session.
        
        Returns:
            True if logout was successful
        """
        token = self.get_stored_token()
        if not token:
            return True  # Already logged out
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(
                    f"{self.proxy_url}/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                ) as response:
                    # Clear local token regardless of server response
                    self.clear_token()
                    return response.status == 200
            except aiohttp.ClientError:
                # Clear local token even if server request fails
                self.clear_token()
                return True
    
    def is_authenticated(self) -> bool:
        """Check if there's a stored token (without validation)."""
        return self.get_stored_token() is not None


# Import asyncio for sleep
import asyncio

# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(DEFAULT_PROXY_URL)
    return _auth_manager
