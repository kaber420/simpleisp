"""
Authentication Middleware
Redirects unauthenticated browser requests to the login page.
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts 401/403 responses and redirects to login
    for browser requests (non-API endpoints).
    """
    
    # Routes that should not trigger redirect (API routes return JSON)
    API_PREFIXES = ("/api/", "/auth/")
    
    # Routes that are public (no auth required)
    PUBLIC_ROUTES = ("/login", "/setup", "/static/")
    
    async def dispatch(self, request: Request, call_next):
        # Let the request proceed normally
        response = await call_next(request)
        
        path = request.url.path
        
        # Skip redirect for API routes (they should return JSON errors)
        if any(path.startswith(prefix) for prefix in self.API_PREFIXES):
            return response
        
        # Skip redirect for public routes
        if any(path.startswith(route) for route in self.PUBLIC_ROUTES):
            return response
        
        # If response is 401 or 403, redirect to login
        if response.status_code in (401, 403):
            return RedirectResponse(url="/login", status_code=302)
        
        return response
