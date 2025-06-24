from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class DatabaseRefreshMiddleware:
    """
    Middleware to ensure fresh database connections and clear caches
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Clear caches before processing request
        try:
            cache.clear()
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
        
        response = self.get_response(request)
        
        # Close database connection after response
        try:
            connection.close()
        except Exception as e:
            logger.warning(f"Failed to close database connection: {e}")
        
        return response 