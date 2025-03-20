"""Resource management module for configuring and managing component dependencies.

This module provides classes to define resources (configurable components) and manage 
their relationships through a provider/requirement dependency model. Resources can
both provide capabilities and require capabilities from other resources, forming
a directed dependency graph.

Key components:
- Resource: Represents a configurable component with capabilities and requirements
- ResourceManager: Manages a catalog of resources and their relationships

This system supports building complex configurations where resources can be
scoped, linked, and managed programmatically.
"""

from typing import Any, Dict, List, Optional, Union

from .exceptions import (
    ResourceDuplicateError,
    ResourceTypeError,
)
from .links import (
    ResourceProviderLink,
    ResourceRequireLink,
)

# import logging

# pylint: disable=relative-beyond-top-level


# Resources implementation
###########################


class Resource:
    """A resource represents a configurable component with dependencies and capabilities.

    This class manages a resource's metadata, dependencies (requires) and capabilities (provides).
    Resources can be linked together through provider/requirement relationships to form
    a dependency graph. Each resource can both provide capabilities to other resources and
    require capabilities from other resources.

    Attributes:
        name (str): Unique identifier for this resource
        scope (str, optional): Namespace/scope this resource belongs to
        provides (list): List of ResourceProviderLink objects representing capabilities this
            resource provides
        requires (list): List of ResourceRequireLink objects representing requirements this
            resource needs
        kwargs (dict): Additional attributes passed during initialization
        **kwargs: Additional attributes dynamically set on the resource, overriding defaults

    Args:
        name (str): Unique identifier for this resource
        scope (str, optional): Namespace/scope this resource belongs to
        provides (list, optional): List of capabilities this resource provides
        requires (list, optional): List of requirements this resource needs
        **kwargs: Additional attributes to set on the resource, overriding defaults

    The provides and requires lists contain configuration dictionaries or strings that
    are converted into ResourceProviderLink and ResourceRequireLink objects respectively.
    Additional attributes are set dynamically based on default_attrs and kwargs.
    """

    default_attrs = {}

    def __init__(
        self,
        name: str,
        scope: Optional[str] = None,
        provides: Optional[List[Dict[str, Any]]] = None,
        requires: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ):
        self.name = name
        self.scope = scope
        self.kwargs = kwargs
        provides = provides or []
        requires = requires or []

        # Assertions
        assert isinstance(self.name, str)
        assert isinstance(self.scope, str) or self.scope is None
        assert isinstance(provides, list)
        assert isinstance(requires, list)

        # Build provider and require links
        self.provides = [
            ResourceProviderLink(config=provide, parent=self) for provide in provides
        ]
        self.requires = [
            ResourceRequireLink(config=require, parent=self) for require in requires
        ]

        # Set extended attributes
        attrs = {}
        attrs.update(self.default_attrs)
        attrs.update(kwargs)
        for attr, value in attrs.items():
            setattr(self, attr, value)

    def __repr__(self) -> str:
        """Return string representation of the resource.

        Returns:
            str: Resource name and scope in format 'Resource(name, scope)'
        """
        return f"Resource({self.name}, {self.scope})"

    def copy(self) -> "Resource":
        """Create a deep copy of this resource.

        Returns:
            Resource: A new Resource instance with copied attributes, provides and requires lists.
                The new instance maintains the same name, scope and additional attributes as
                the original.
        """
        return self.__class__(
            self.name,
            scope=self.scope,
            provides=list(self.provides),
            requires=list(self.requires),
            **self.kwargs,
        )


class ResourceManager:
    """Manages a catalog of resources and their relationships.

    This class provides functionality to store, retrieve and manage resources and their
    configurations. Resources can be organized by scopes and can be added either as
    Resource objects or configuration dictionaries. It supports adding individual resources
    or collections of resources, and retrieving resources by name or scope.

    Args:
        catalog (dict, optional): Initial catalog of resources. Defaults to empty dict.

    Attributes:
        catalog (dict): Dictionary storing all resources, keyed by resource name.
        resource_class (Resource): The resource class to use when creating new resources.
    """

    resource_class: Resource = Resource

    def __init__(self, catalog: Optional[Dict[str, Resource]] = None):
        self.catalog = catalog or {}

    def dump_catalog(self) -> Dict[str, Resource]:
        """Returns a copy of the entire resource catalog.

        Returns:
            dict: A dictionary copy of the current resource catalog.
        """
        return dict(self.catalog)

    def add_resource(
        self,
        name: str,
        scope: Optional[str] = None,
        config: Optional[Union[Dict[str, Any], Resource]] = None,
        force: bool = False,
    ) -> None:
        """Adds a new resource to the catalog.

        Args:
            name (str): Unique name for the resource.
            scope (str, optional): Scope to organize resources. Defaults to None.
            config (Union[dict, Resource], optional): Resource configuration or Resource instance.
                Defaults to empty dict.
            force (bool, optional): If True, allows overwriting existing resources.
                Defaults to False.

        Raises:
            ResourceTypeError: If name is not a string or config is invalid type
            ResourceDuplicateError: If resource already exists (when force=False).
        """
        if not isinstance(name, str):
            raise ResourceTypeError(f"Expected str, got: {type(name)}={name}")
        config = config or {}

        new_val = None
        if isinstance(config, Resource):
            new_val = config.copy()
            new_val.scope = scope
            new_val.name = name
        elif isinstance(config, dict):
            new_val = self.resource_class(name, scope, **config)

        if not isinstance(new_val, Resource):
            raise ResourceTypeError(f"Expected Resource, got: {type(config)}={config}")

        # Temporary workaround to avoid duplicate resources
        if not force and name in self.catalog:
            raise ResourceDuplicateError(f"Duplicate resource: {name}")

        self.catalog[name] = new_val

    def add_resources(
        self,
        resources: Dict[str, Union[Dict[str, Any], Resource]],
        scope: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Adds multiple resources to the catalog.

        Args:
            resources (dict): Dictionary of resources where keys are resource names
                and values are resource configurations or Resource instances.
            scope (str, optional): Scope to assign to all added resources. Defaults to None.

        Raises:
            ResourceTypeError: If resources is not a dict or if any resource config is invalid.
        """
        if not isinstance(resources, dict):
            raise ResourceTypeError(
                f"Expected dict, got: {type(resources)}={resources}"
            )
        for name, config in resources.items():
            if not isinstance(name, str):
                raise ResourceTypeError(f"Expected str, got: {type(name)}={name}")
            if not isinstance(config, (dict, Resource)):
                raise ResourceTypeError(
                    f"Expected dict or Resource, got: {type(config)}={config}"
                )
            self.add_resource(name, scope=scope, config=config, force=force)

    def get_resource(self, name: str) -> Resource:
        """Retrieves a specific resource from the catalog.

        Args:
            name (str): Name of the resource to retrieve.

        Returns:
            Resource: The requested resource instance.

        Raises:
            KeyError: If resource name doesn't exist in catalog.
        """
        return self.catalog[name]

    def get_resources(
        self, scope: Optional[str] = None
    ) -> Union[Dict[str, Resource], List[Resource]]:
        """Retrieves all resources, optionally filtered by scope.

        Args:
            scope (str, optional): Scope to filter resources by. Defaults to None.

        Returns:
            Union[dict, list]: If scope is None, returns dict of all resources.
                If scope is specified, returns list of resources in that scope.
        """
        if scope is None:
            return dict(self.catalog)
        return [x for x in self.catalog.values() if x.scope == scope]

    def get_resource_scopes(self) -> List[str]:
        """Gets list of all unique scopes used in the catalog.

        Returns:
            list: List of unique scope names.
        """
        return list({x.scope for x in self.catalog.values()})

    def __iter__(self) -> Any:
        """Makes ResourceManager iterable over its resources.

        Returns:
            iterator: Iterator over resource values in catalog.
        """
        return iter(self.catalog.values())

    def copy(self) -> "ResourceManager":
        """Creates a deep copy of the ResourceManager.

        Returns:
            ResourceManager: New ResourceManager instance with copied catalog.
        """
        return self.__class__(self.dump_catalog())
