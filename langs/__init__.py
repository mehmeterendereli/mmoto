"""
Dil paketi - MMoto uygulaması için çoklu dil desteğini içerir
"""

from .language_manager import language_manager, get_text

# Kolay erişim için
_ = get_text

__all__ = ['language_manager', 'get_text', '_'] 