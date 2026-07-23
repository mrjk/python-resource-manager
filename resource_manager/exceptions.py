"""
Resource Manager Exceptions Module

This module defines the exception hierarchy used by the resource manager system.
It provides specialized exceptions for different error scenarios that may occur
during resource configuration, linking, resolution, and implementation.
"""

# Custom exceptions
###########################


class ResourceManagerError(Exception):
    """Base exception for all resource manager errors."""


class ResourceConfigError(ResourceManagerError):
    """Raised when there's an error in resource configuration."""


class ResourceTypeError(ResourceConfigError):
    """Raised when a resource has an invalid type."""


class ResourceLinkError(ResourceManagerError):
    """Raised when there's an error in resource linking.

    Optional ``binding_trace`` carries the explainable match attempt when the
    failure came from cardinality / selection (pin, remap, default, schema).
    """

    def __init__(self, message: str, binding_trace=None):
        super().__init__(message)
        self.binding_trace = binding_trace


class ResourceDuplicateError(ResourceManagerError):
    """Raised when a duplicate resource is found."""


class ResourceResolutionError(ResourceManagerError):
    """Raised when there's an error in dependency resolution."""


class ResourceImplementationError(ResourceManagerError):
    """Raised when a method implementation is missing."""
