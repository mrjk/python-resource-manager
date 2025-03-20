"""Resource dependency resolution system for the resource manager.

This module implements a dependency resolution system for resources that have provider and
requirement relationships. It provides functionality to:

1. Build a complete resource dependency graph
2. Resolve dependencies between resources with matching requirements and capabilities
3. Determine the correct initialization order based on topological sorting
4. Visualize dependency relationships as graphs

The core classes are:
- EdgeLink: Represents a connection between a resource requirement and a provider
- DepBuilder: Main dependency resolver that builds the graph and determines initialization order

The module supports flexible dependency resolution strategies through subclassing, with the
ability to customize how requirements are matched with providers through the resolve_requirements
method.
"""

from graphlib import TopologicalSorter
from typing import Any, Dict, List, Optional, Tuple, Union

import pydot

from .exceptions import (
    ResourceDuplicateError,
    ResourceImplementationError,
    ResourceResolutionError,
    ResourceTypeError,
)
from .links import (
    ResourceProviderLink,
    ResourceRequireLink,
)
from .resources import (
    Resource,
    ResourceManager,
)

# pylint: disable=relative-beyond-top-level




# Resource resolver implementation
###########################


class EdgeLink:
    """Represents a directed edge between a requirement and provider in the dependency graph.

    This class models the connection between a resource requirement and the provider that fulfills
    it. It maintains information about the specific instance, requirement link, and provider link
    that form the dependency relationship.

    In the dependency resolution process:
    1. Each Resource has one or more ResourceRequireLink objects (requirements)
    2. Each Resource has one or more ResourceProviderLink objects (capabilities)
    3. During resolution, requirements are matched with compatible providers
    4. For each match, an EdgeLink is created to represent this dependency relationship
    5. The EdgeLink connects a requiring resource to a providing resource

    Args:
        inst (str): The instance name that this edge connects
        requirement (ResourceRequireLink): The requirement link from the dependent resource
        provider (ResourceProviderLink): The provider link from the providing resource

    Attributes:
        inst (str): Instance name for this edge connection
        requirement (ResourceRequireLink): Reference to the requirement link
        provider (ResourceProviderLink): Reference to the provider link that satisfies the
            requirement
    """

    def __init__(
        self,
        inst: str,
        requirement: ResourceRequireLink,
        provider: ResourceProviderLink,
    ):
        self.inst = inst
        self.requirement = requirement
        self.provider = provider

    @property
    def rule(self) -> str:
        """Generates a canonical rule string representing this edge connection.

        The rule combines the requirement kind, instance name, and modifier into a
        standardized format that uniquely identifies this edge in the dependency graph.

        Returns:
            str: Rule string in format "<kind>.<instance>.<modifier>" where:
                - kind is the requirement's resource type
                - instance is this edge's instance name or "DEFAULT"
                - modifier is the requirement's cardinality modifier or "DEFAULT"
        """
        return (
            f"{self.requirement.kind}."
            f"{self.inst or 'DEFAULT'}."
            f"{self.requirement.mod or 'DEFAULT'}"
        )

    def __repr__(self) -> str:
        """Creates a string representation of this edge link.

        Returns:
            str: String showing the requirement resource name, rule, and provider resource name
                in format "EdgeLink(<req_resource>:<rule> -> <prov_resource>)"
        """
        return (
            f"EdgeLink({self.requirement.resource.name}:{self.rule} -> "
            f"{self.provider.resource.name})"
        )


# pylint: disable=too-many-instance-attributes
class DepBuilder:
    """Dependency builder for resolving resource dependencies and generating dependency graphs.

    This class manages the process of resolving dependencies between resources, building
    a dependency tree, and determining the correct order for resource initialization.
    It supports visualization of the dependency graph for debugging and analysis.

    The resolution process involves:
    1. Building a list of all provider links from resources
    2. Starting from a build context resource, recursively resolving all dependencies
    3. Creating a simplified dependency tree with resource names
    4. Using topological sorting to determine the correct initialization order

    Attributes:
        remap_rules (dict): Rules for remapping resource kinds to default instance names
        feature_names (list): List of feature names to include in the dependency resolution
        debug (bool): Flag to enable debug output during resolution
        rmanager (ResourceManager): Manager containing all resources to be resolved
        resolved (bool): Flag indicating whether resolution has been performed
        provider_links (list): List of all provider links from resources
        dep_tree (dict): Complete dependency tree with EdgeLink objects
        dep_topo (dict): Simplified dependency tree with resource names only
        dep_order (list): Ordered list of resources based on dependency resolution
        resource_manager_class (ResourceManager): Class to use for resource management

    Args:
        resources (Union[ResourceManager, dict], optional): Initial resources to manage.
            Can be a ResourceManager instance or a dictionary of resources. Defaults to None.
        feature_names (list, optional): List of feature names to include. Defaults to None.
        remap_rules (dict, optional): Rules for remapping resource kinds. Defaults to None.
        debug (bool, optional): Enable debug output. Defaults to False.
    """

    resource_manager_class: ResourceManager = ResourceManager

    def __init__(
        self,
        resources: Optional[Union[ResourceManager, Dict[str, Resource]]] = None,
        root_name: Optional[str] = "__root__",
        feature_names: Optional[List[str]] = None,
        remap_rules: Optional[Dict[str, str]] = None,
        debug: bool = False,
    ):

        self.root_node_name = root_name or "__builder__"
        self.remap_rules = remap_rules or {}
        self.feature_names = feature_names or []
        self.debug = debug

        resources = resources or {}
        if isinstance(resources, ResourceManager):
            self.rmanager = resources.copy()
        else:
            self.rmanager = self.resource_manager_class()
            self.rmanager.add_resources(resources, scope="APP")

        # Prepare state attributes
        self.resolved = False
        self.provider_links = None
        self.dep_tree = None
        self.dep_topo = None
        self.dep_order = None

    def add_resources(
        self,
        config: Dict[str, Union[Dict[str, Any], Resource]],
        scope: str = "APP_EXTRA",
    ) -> None:
        """Add resources to the resource manager.

        This method adds new resources to the internal resource manager with the specified scope.

        Args:
            config (dict): Dictionary of resources to add, where keys are resource names
                and values are resource configurations or Resource instances
            scope (str, optional): Scope to assign to all added resources. Defaults to "APP_EXTRA".
        """
        self.rmanager.add_resources(config, scope=scope)

    def resolve(
        self,
        remap_rules: Optional[Dict[str, str]] = None,
        feature_names: Optional[List[str]] = None,
        extra_resources: Optional[Dict[str, Union[Dict[str, Any], Resource]]] = None,
    ) -> None:
        """Resolve dependencies between resources.

        This method performs the dependency resolution process, building the dependency tree
        and determining the correct order for resource initialization. It can only be called
        once per DepBuilder instance to ensure idempotency.

        Args:
            remap_rules (dict, optional): Rules for remapping resource kinds, overriding
                the instance's remap_rules. Defaults to None.
            feature_names (list, optional): List of feature names to include, overriding
                the instance's feature_names. Defaults to None.
            extra_resources (dict, optional): Additional resources to add before resolution.
                Defaults to None.

        Raises:
            ResourceResolutionError: If resolution has already been performed on this instance.
        """
        # Resolution can only happen once per object to ensure idempotency
        if self.resolved:
            raise ResourceResolutionError("Already resolved")
        self.resolved = True

        # Fetch argument overrides
        remap_rules = remap_rules or self.remap_rules
        feature_names = feature_names or self.feature_names

        # Append extra resources
        if extra_resources:
            self.rmanager.add_resources(extra_resources, scope="APP_EXTRA")

        self.rmanager.add_resource(
            self.root_node_name or "__builder__",
            scope="BUILDER",
            config={
                "desc": "Temporary build context",
                "requires": feature_names,
                "group": "__internal__",
            },
            force=True,
        )

        # Run resolver
        self._resolve()

    def _resolve(self) -> None:
        """Internal method to drive the resolution process.

        This method orchestrates the dependency resolution process by:
        1. Building the list of provider links from all resources
        2. Constructing the complete dependency tree
        3. Creating a simplified dependency tree
        4. Determining the correct order for resource initialization

        This is meant to be overridden by subclasses to customize the resolution process.
        """
        # Resolve tree
        self.provider_links = self._build_provider_links()
        self.dep_tree = self._get_dependencies(debug=self.debug)

        self.dep_topo = self._get_simplified_tree(self.dep_tree)
        self.dep_order = self._get_dependencies_order(self.dep_topo)

    def _build_provider_links(self) -> List[ResourceProviderLink]:
        """Build a list of all provider links from resources.

        This method collects all ResourceProviderLink objects from all resources
        in the resource manager, which represent capabilities that resources provide.

        Returns:
            list: List of ResourceProviderLink objects from all resources

        Raises:
            ResourceTypeError: If any resource or provider link is not of the expected type
        """
        resources_catalog = self.rmanager

        # Build providers list
        provider_links = []
        for feat_config in resources_catalog:
            if not isinstance(feat_config, Resource):
                raise ResourceTypeError(
                    f"Expected Resource, got: {type(feat_config)}={feat_config}"
                )
            for provide in feat_config.provides:
                if not isinstance(provide, ResourceProviderLink):
                    raise ResourceTypeError(
                        f"Expected ResourceProviderLink, got: {type(provide)}={provide}"
                    )
                provider_links.append(provide)

        return provider_links

    def _get_dependencies(self, debug: bool = False) -> Dict[str, List[EdgeLink]]:
        """Build the complete dependency tree for all resources.

        This method starts from the build context resource and recursively resolves
        all dependencies, building a complete tree of resource dependencies.

        Args:
            debug (bool, optional): Whether to print debug information about the
                resolution process. Defaults to False.

        Returns:
            dict: Complete dependency tree where keys are resource names and values
                are lists of EdgeLink objects representing dependencies
        """
        out_tree = {}
        resolve_tree_report = []
        self.resolve_resources_tree(
            self.root_node_name or "__builder__", dep_tree=out_tree, report=resolve_tree_report
        )
        if not self.root_node_name:
            out_tree.pop(self.root_node_name)

        if debug:
            print("Resolution tree:")
            print("\n".join(resolve_tree_report))
        return out_tree

    def resolve_resources_tree(
        self,
        resource_name: str,
        dep_tree: Optional[Dict[str, List[EdgeLink]]] = None,
        lvl: int = 0,
        report: Optional[List[str]] = None,
    ) -> None:
        """Recursively resolve the dependency tree for a resource.

        This method resolves all dependencies for a given resource and adds them to the
        dependency tree. It recursively resolves dependencies for each dependency that
        hasn't been resolved yet.

        Args:
            resource_name (str): Name of the resource to resolve
            dep_tree (dict, optional): Current dependency tree to add to. If None,
                a new tree will be created. Defaults to None.
            lvl (int, optional): Current recursion level for indentation in reports.
                Defaults to 0.
            report (list, optional): List to collect resolution reports for debugging.
                Defaults to None.

        Raises:
            ResourceTypeError: If the dependency tree is not a dict
            ResourceDuplicateError: If a resource appears multiple times in the
                tree (cyclic dependency)
        """
        # Reporting
        if report is None:
            report = []
        indent = "  " * lvl
        report.append(f"{indent}|_ Resolve: {resource_name}")

        # Build tree
        dep_tree = {} if dep_tree is None else dep_tree
        if not isinstance(dep_tree, dict):
            raise ResourceTypeError("Dependency tree must be a dict")

        # Fetch resource by name
        resource = self.rmanager.get_resource(resource_name)
        if resource_name in dep_tree:
            raise ResourceDuplicateError(f"Duplicate resource: {resource_name}")

        # Resolve requirements
        dep_tree[resource_name] = []
        for requirement in resource.requires:
            # Get provider links that satisfy this requirement
            match_name, provider_links = self.resolve_requirements(requirement, lvl=lvl)

            # For each provider that can satisfy this requirement
            for provider_link in provider_links:
                # Create an edge representing this dependency
                edge = EdgeLink(
                    inst=match_name, requirement=requirement, provider=provider_link
                )
                dep_tree[resource_name].append(edge)

                # Resolve children if not already done
                provider_resource_name = provider_link.resource.name
                if provider_resource_name not in dep_tree:
                    self.resolve_resources_tree(
                        provider_resource_name,
                        dep_tree=dep_tree,
                        lvl=lvl + 1,
                        report=report,
                    )

    def resolve_requirements(
        self, requirement: ResourceRequireLink, lvl: int = 0
    ) -> Tuple[str, List[ResourceProviderLink]]:
        """Resolve a requirement against available providers.

        This method matches a requirement against available provider links to find
        compatible providers. It must be implemented by subclasses to define the
        specific matching logic for resolving dependencies.

        The actual implementation should:
        1. Identify providers that match the requirement's kind
        2. Apply any instance name remapping based on remap_rules
        3. Filter matches based on instance names
        4. Validate match cardinality against the requirement's modifier

        Args:
            requirement (ResourceRequireLink): The requirement to resolve
            lvl (int, optional): Current recursion level for debugging output. Defaults to 0.

        Returns:
            tuple: A tuple containing:
                - str: The resolved requirement name after any remapping
                - list: List of ResourceProviderLink objects that satisfy this requirement

        Raises:
            ResourceImplementationError: This method must be implemented by subclasses
        """
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )

        return match_name, provider_links
    
    def _get_simplified_tree(self, dep_tree) -> dict:
        """Create a simplified dependency tree with resource names only.

        This method converts the complete dependency tree with EdgeLink objects
        to a simplified tree with resource names only, suitable for topological sorting.

        Args:
            dep_tree (dict): Complete dependency tree with EdgeLink objects

        Returns:
            dict: Simplified dependency tree where keys are resource names and values
                are lists of resource names they depend on
        """
        simplified_tree = {}
        for key, deps in dep_tree.items():
            simplified_tree[key] = [x.provider.resource.name for x in deps]
        return simplified_tree

    def _get_dependencies_order(self, dep_topo) -> list:
        """Determine the correct order for resource initialization.

        This method performs a topological sort on the simplified dependency tree
        to determine the correct order for resource initialization, ensuring that
        all dependencies are initialized before the resources that depend on them.

        Args:
            dep_topo (dict): Simplified dependency tree where keys are resource names
                and values are lists of resource names they depend on

        Returns:
            list: Ordered list of resource names based on dependency resolution
        """
        graph = TopologicalSorter(dep_topo)
        ret = list(graph.static_order())
        return ret

    # Public API
    # ===============

    def gen_graph(self, output_file: str = "output.png") -> None:
        """Generate a visual representation of the dependency graph.

        This method creates a PNG image visualizing the dependency graph, showing
        resources as nodes and dependencies as directed edges. The graph is laid out
        from right to left, with dependencies pointing to the resources that require them.

        Args:
            output_file (str, optional): Path to save the generated PNG image.
                Defaults to "output.png".

        Note:
            This method requires the pydot library and GraphViz to be installed.
        """
        dep_tree = self.dep_tree

        # Create a root directed graph
        graph = pydot.Dot(
            "my_graph",
            layout="dot",
            rankdir="RL",
            # compound=,
            graph_type="digraph",
            newrank=True,
            bgcolor="white",
        )

        # Add nodes for each resource
        for resource_name in self.dep_order:
            node = pydot.Node(
                resource_name,
                shape="box",
            )
            graph.add_node(node)

        # Add edges for each dependency
        for resource_name in self.dep_order:
            edges = dep_tree[resource_name]

            for edge in edges:
                dependency_name = edge.provider.resource.name
                label = f"{edge.rule}"
                edge = pydot.Edge(dependency_name, resource_name, label=label)
                graph.add_edge(edge)

        # Save the graph to a file
        graph.write(output_file, format="png")
