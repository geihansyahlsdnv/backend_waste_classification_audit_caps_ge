from fastapi import Request, Response
from typing import Callable
import time
from ..services.logger_service import logger_service

async def logging_middleware(request: Request, call_next: Callable) -> Response:
    start_time = time.time()
    
    user_id = None
    try:
        if "Authorization" in request.headers:
            from ..core.security import decode_token
            token = request.headers["Authorization"].split(" ")[1]
            payload = decode_token(token)
            user_id = payload["sub"]
    except:
        pass
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger_service.log_request(request, response, duration, user_id)
        return response
    except Exception as e:
        logger_service.log_error(e, request, user_id)
        raise