"""
Internationalization (i18n) Support for Rocket CLI

Provides multi-language support using gettext for global accessibility.
Supports automatic language detection and manual language selection.

Supported Languages:
- en: English (default)
- es: Spanish
- fr: French
- de: German
- zh: Chinese (Simplified)
- ja: Japanese
- pt: Portuguese

Usage:
    from Rocket.Utils.i18n import _, set_language, get_available_languages
    
    # Use translated strings
    print(_("Hello, World!"))
    
    # Change language
    set_language('es')
    print(_("Hello, World!"))  # Prints: "¡Hola, Mundo!"
"""

import gettext
import locale
import os
from pathlib import Path
from typing import Optional, List, Callable
from functools import lru_cache

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)

# Localization directory
LOCALE_DIR = Path(__file__).parent.parent.parent / "locales"

# Current language and translation function
_current_lang: str = "en"
_translations: Optional[gettext.GNUTranslations] = None
_translation_function: Callable[[str], str] = lambda x: x


def get_system_language() -> str:
    """
    Detect system default language.
    
    Returns:
        Two-letter language code (e.g., 'en', 'es', 'fr')
    """
    try:
        # Get system locale
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            # Extract language code (e.g., 'en_US' -> 'en')
            lang_code = system_locale.split('_')[0].lower()
            if lang_code in get_available_languages():
                return lang_code
    except Exception as e:
        logger.debug(f"Could not detect system language: {e}")
    
    return "en"  # Default to English


@lru_cache(maxsize=1)
def get_available_languages() -> List[str]:
    """
    Get list of available language codes.
    
    Returns:
        List of two-letter language codes
    """
    languages = ["en"]  # English always available
    
    if LOCALE_DIR.exists():
        for item in LOCALE_DIR.iterdir():
            if item.is_dir() and (item / "LC_MESSAGES" / "rocket.mo").exists():
                languages.append(item.name)
    
    return sorted(languages)


def set_language(lang_code: str) -> bool:
    """
    Set the current language for the CLI.
    
    Args:
        lang_code: Two-letter language code (e.g., 'en', 'es', 'fr')
        
    Returns:
        True if language was set successfully, False otherwise
    """
    global _current_lang, _translations, _translation_function
    
    # Validate language code
    if lang_code not in get_available_languages():
        logger.warning(f"Language '{lang_code}' not available. Using English.")
        lang_code = "en"
    
    try:
        if lang_code == "en":
            # English - no translation needed
            _translations = None
            _translation_function = lambda x: x
        else:
            # Load translation file
            _translations = gettext.translation(
                'rocket',
                localedir=str(LOCALE_DIR),
                languages=[lang_code],
                fallback=True
            )
            _translation_function = _translations.gettext
        
        _current_lang = lang_code
        logger.info(f"Language set to: {lang_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load language '{lang_code}': {e}")
        # Fallback to English
        _translations = None
        _translation_function = lambda x: x
        _current_lang = "en"
        return False


def get_current_language() -> str:
    """
    Get the currently active language code.
    
    Returns:
        Two-letter language code
    """
    return _current_lang


def _(message: str) -> str:
    """
    Translate a message to the current language.
    
    This is the main translation function used throughout the CLI.
    
    Args:
        message: English message to translate
        
    Returns:
        Translated message in current language
    """
    return _translation_function(message)


# Translation wrapper with formatting support
def translate(message: str, **kwargs) -> str:
    """
    Translate and format a message with named placeholders.
    
    Args:
        message: English message with {placeholders}
        **kwargs: Values for placeholders
        
    Returns:
        Translated and formatted message
        
    Example:
        translate("Hello, {name}!", name="Alice")
        # Spanish: "¡Hola, Alice!"
    """
    translated = _(message)
    if kwargs:
        try:
            return translated.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing placeholder in translation: {e}")
            return translated
    return translated


def get_language_name(lang_code: str) -> str:
    """
    Get the native name of a language.
    
    Args:
        lang_code: Two-letter language code
        
    Returns:
        Native language name
    """
    language_names = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "zh": "中文",
        "ja": "日本語",
        "pt": "Português",
        "it": "Italiano",
        "ru": "Русский",
        "ko": "한국어",
        "ar": "العربية",
        "hi": "हिन्दी",
        "te": "తెలుగు",
        "ta": "தமிழ்",
        "ro": "Română"
    }
    return language_names.get(lang_code, lang_code.upper())


# Initialize with system language on import
try:
    system_lang = get_system_language()
    set_language(system_lang)
except Exception as e:
    logger.debug(f"Failed to initialize language: {e}")
    set_language("en")
