"""
Models package - Data layer (MVC Architecture)
Contains data models and database/storage interactions
"""

from .device import Device
from .test_result import TestResult

__all__ = ['Device', 'TestResult']
