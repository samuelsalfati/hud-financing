"""
IRR and MOIC calculation utilities
Re-exports from cashflows for backward compatibility
"""
from .cashflows import calculate_irr, calculate_moic

__all__ = ['calculate_irr', 'calculate_moic']
