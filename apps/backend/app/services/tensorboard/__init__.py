"""
TensorBoard Services

Services for managing TensorBoard instances, including:
- Instance lifecycle management
- Kubernetes deployment
- URL proxy and access control
"""

from .manager import TensorBoardManager
from .proxy import TensorBoardProxy

__all__ = ["TensorBoardManager", "TensorBoardProxy"]
