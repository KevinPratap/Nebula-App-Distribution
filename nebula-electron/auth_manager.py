"""
Authentication Manager for Nebula Prompter Pro
Handles secure credential storage and authentication
"""
import keyring
from typing import Optional, Tuple
import json

class AuthManager:
    """Manages user authentication and credential storage"""
    
    SERVICE_NAME = "NebulaPro"
    REMEMBER_ME_KEY = "remember_me_email"
    
    @staticmethod
    def save_credentials(email: str, password: str, remember_me: bool = False) -> None:
        """
        Save user credentials securely
        
        Args:
            email: User email address
            password: User password
            remember_me: Whether to persist credentials
        """
        if remember_me:
            # Store in OS credential manager
            keyring.set_password(AuthManager.SERVICE_NAME, email, password)
            # Save email for auto-fill
            keyring.set_password(AuthManager.SERVICE_NAME, AuthManager.REMEMBER_ME_KEY, email)
        else:
            # Clear any saved credentials
            AuthManager.clear_saved_credentials()
    
    @staticmethod
    def load_saved_credentials() -> Optional[Tuple[str, str]]:
        """
        Load saved credentials if "Remember Me" was checked
        
        Returns:
            Tuple of (email, password) if saved, None otherwise
        """
        try:
            # Check if we have a saved email
            saved_email = keyring.get_password(AuthManager.SERVICE_NAME, AuthManager.REMEMBER_ME_KEY)
            if saved_email:
                # Get the password for that email
                saved_password = keyring.get_password(AuthManager.SERVICE_NAME, saved_email)
                if saved_password:
                    return (saved_email, saved_password)
        except Exception:
            pass
        return None
    
    @staticmethod
    def clear_saved_credentials() -> None:
        """Clear all saved credentials"""
        try:
            # Get saved email if any
            saved_email = keyring.get_password(AuthManager.SERVICE_NAME, AuthManager.REMEMBER_ME_KEY)
            if saved_email:
                # Delete password
                try:
                    keyring.delete_password(AuthManager.SERVICE_NAME, saved_email)
                except Exception:
                    pass
                # Delete email marker
                try:
                    keyring.delete_password(AuthManager.SERVICE_NAME, AuthManager.REMEMBER_ME_KEY)
                except Exception:
                    pass
        except Exception:
            pass
    
    @staticmethod
    def validate_login(email: str, password: str) -> Tuple[bool, dict]:
        """
        Validate credentials with the Nebula Authorization Server
        """
        try:
            from monetization_manager import MonetizationManager
            
            # Attempt login (this will automatically save the token to session.json)
            success, message = MonetizationManager.login(email, password)
            
            if success:
                # Get the user info we just fetched/stored
                valid, info = MonetizationManager.validate_session()
                if valid:
                    return (True, info)
            
            return (False, {"error": message})
            
        except ImportError:
            return (False, {"error": "Monetization module missing."})
        except Exception as e:
            return (False, {"error": str(e)})
