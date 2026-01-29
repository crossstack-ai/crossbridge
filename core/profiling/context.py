"""
Profiling Context Managers and Decorators

Easy-to-use wrappers for profiling code sections.
"""

import functools
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
import asyncio

from .base import Profiler
from .factory import get_profiler
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


@contextmanager
def profile(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    profiler: Optional[Profiler] = None
):
    """
    Profile a code section (context manager).
    
    Usage:
        with profile("semantic_search", {"query_len": len(query)}):
            results = do_search(query)
    
    Args:
        name: Profile section name
        metadata: Optional metadata to attach
        profiler: Profiler instance (uses global if None)
    """
    if profiler is None:
        profiler = get_profiler()
    
    profiler.start(name, metadata)
    try:
        yield
    finally:
        profiler.stop(name, metadata)


@contextmanager
async def profile_async(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    profiler: Optional[Profiler] = None
):
    """
    Profile an async code section (async context manager).
    
    Usage:
        async with profile_async("async_search"):
            results = await async_search()
    
    Args:
        name: Profile section name
        metadata: Optional metadata to attach
        profiler: Profiler instance (uses global if None)
    """
    if profiler is None:
        profiler = get_profiler()
    
    profiler.start(name, metadata)
    try:
        yield
    finally:
        profiler.stop(name, metadata)


def profiled(
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    profiler: Optional[Profiler] = None
):
    """
    Decorator for profiling functions.
    
    Usage:
        @profiled("semantic_search")
        def search(query):
            return do_search(query)
        
        # Or auto-name from function
        @profiled()
        def search(query):  # Will use "search" as name
            return do_search(query)
    
    Args:
        name: Profile name (uses function name if None)
        metadata: Optional metadata to attach
        profiler: Profiler instance (uses global if None)
    """
    def decorator(func: Callable) -> Callable:
        profile_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            p = profiler or get_profiler()
            
            with profile(profile_name, metadata, p):
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def profiled_async(
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    profiler: Optional[Profiler] = None
):
    """
    Decorator for profiling async functions.
    
    Usage:
        @profiled_async("async_search")
        async def search(query):
            return await async_search(query)
    
    Args:
        name: Profile name (uses function name if None)
        metadata: Optional metadata to attach
        profiler: Profiler instance (uses global if None)
    """
    def decorator(func: Callable) -> Callable:
        profile_name = name or func.__name__
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            p = profiler or get_profiler()
            
            p.start(profile_name, metadata)
            try:
                return await func(*args, **kwargs)
            finally:
                p.stop(profile_name, metadata)
        
        return wrapper
    
    return decorator


class ProfilerContext:
    """
    Profiler context for manual start/stop.
    
    Usage:
        ctx = ProfilerContext("semantic_search")
        ctx.start()
        try:
            do_work()
        finally:
            ctx.stop()
    
    Or as context manager:
        with ProfilerContext("semantic_search"):
            do_work()
    """
    
    def __init__(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        profiler: Optional[Profiler] = None
    ):
        self.name = name
        self.metadata = metadata
        self.profiler = profiler or get_profiler()
    
    def start(self) -> None:
        """Start profiling"""
        self.profiler.start(self.name, self.metadata)
    
    def stop(self) -> None:
        """Stop profiling"""
        self.profiler.stop(self.name, self.metadata)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
