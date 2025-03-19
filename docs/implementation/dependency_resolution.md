# Dependency Resolution

This document explains how dependency resolution works in the Resource Manager, focusing on the algorithm that connects requirements to providers and determines initialization order.

## DepBuilder Class

The `DepBuilder` class is responsible for resolving dependencies between resources:

```python
class DepBuilder:
    def __init__(self, resources, feature_names=None, remap_rules=None, debug=False):
        self.rmanager = resources
        self.feature_names = feature_names or []
        self.remap_rules = remap_rules or {}
        self.debug = debug
        
        # Resolution results
        self.dep_tree = {}   # Resource name -> list of EdgeLinks
        self.dep_order = []  # Ordered list of resource names
        self.provider_links = []  # All provider links
```

## Resolution Algorithm

The dependency resolution process consists of several key steps:

### 1. Building Provider Links

First, the resolver collects all provider links from the resources:

```python
def _build_provider_links(self):
    """Build a flat list of all provider links."""
    self.provider_links = []
    
    for resource_name in self.rmanager.catalog:
        resource = self.rmanager.get_resource(resource_name)
        self.provider_links.extend(resource.get_provider_links())
```

### 2. Starting Resolution

The resolution process begins with the specified feature requirements:

```python
def _resolve(self):
    """Execute the resolution process."""
    self._build_provider_links()
    
    # Start with feature requirements if specified
    if self.feature_names:
        for feature_name in self.feature_names:
            self._resolve_feature(feature_name)
```

### 3. Resolving Features

For each specified feature, the resolver attempts to find matching providers:

```python
def _resolve_feature(self, feature_name):
    """Resolve a specific feature requirement."""
    # Create a synthetic requirement
    parts = feature_name.split(".")
    if len(parts) == 1:
        # Just a kind, no instance
        requirement = ResourceRequireLink(parts[0], mod="!")
    else:
        # Has both kind and instance
        kind = parts[0]
        instance = ".".join(parts[1:])
        requirement = ResourceRequireLink(kind, instance, mod="!")
    
    # Resolve this requirement
    match_name, provider_links = self.resolve_requirements(requirement)
    
    # Process each matching provider
    for provider in provider_links:
        resource = provider.resource
        self._process_resource(resource)
```

### 4. Processing Resources

For each matched resource, the resolver processes its requirements:

```python
def _process_resource(self, resource, lvl=0):
    """Process a resource's requirements."""
    # Skip if already processed
    if resource.name in self.dep_tree:
        return
    
    # Initialize resource's entry in the dependency tree
    self.dep_tree[resource.name] = []
    
    # Process each requirement
    for requirement in resource.get_requirement_links():
        # Resolve this requirement
        match_name, provider_links = self.resolve_requirements(requirement, lvl + 1)
        
        # Add edges for each matching provider
        for provider in provider_links:
            edge = EdgeLink(requirement, provider, match_name)
            self.dep_tree[resource.name].append(edge)
            
            # Process the provider's resource
            provider_resource = provider.resource
            self._process_resource(provider_resource, lvl + 1)
```

### 5. Resolving Requirements

The core of the resolution process is matching requirements with providers:

```python
def resolve_requirements(self, requirement, lvl=0):
    """Resolve a requirement to matching providers."""
    # Match providers using the requirement's matching logic
    match_name, provider_links = requirement.match_provider(
        self.provider_links,
        remap_rules=self.remap_rules,
        default_mode="one",
        remap_requirement=True,
    )
    
    return match_name, provider_links
```

### 6. Determining Initialization Order

After building the dependency tree, the resolver determines the correct initialization order:

```python
def _compute_dep_order(self):
    """Compute the dependency initialization order."""
    if not self.dep_tree:
        return []
    
    # Build a directed graph
    graph = {}
    for resource_name, edges in self.dep_tree.items():
        if resource_name not in graph:
            graph[resource_name] = set()
        
        for edge in edges:
            provider_name = edge.provider.resource.name
            if provider_name not in graph:
                graph[provider_name] = set()
            
            # Resource depends on provider
            graph[resource_name].add(provider_name)
    
    # Topological sort
    visited = set()
    temp_visited = set()
    order = []
    
    def visit(node):
        if node in temp_visited:
            raise ValueError(f"Circular dependency detected involving {node}")
        
        if node in visited:
            return
        
        temp_visited.add(node)
        
        for dependency in graph[node]:
            visit(dependency)
        
        temp_visited.remove(node)
        visited.add(node)
        order.append(node)
    
    # Visit all nodes
    for node in graph:
        if node not in visited:
            visit(node)
    
    # Reverse the order since we want dependencies first
    return list(reversed(order))
```

## Resolution Process

When the `resolve()` method is called, the resolver:

1. Builds the list of all provider links
2. Resolves the specified feature requirements
3. Processes each matched resource and its requirements
4. Builds a dependency tree representing the resolved connections
5. Computes the correct initialization order
6. Returns the ordered list of resource names

```python
def resolve(self):
    """Execute the full resolution process."""
    self._resolve()
    self.dep_order = self._compute_dep_order()
    return self.dep_order
```

## Extension Points

The `DepBuilder` class is designed to be extensible through subclassing. The main extension point is the `resolve_requirements` method:

```python
class CustomDepBuilder(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        """Custom implementation for resolving requirements."""
        # Add custom logic here
        
        # Then call the parent method or implement custom matching
        return super().resolve_requirements(requirement, lvl)
```

## Implementation Details

Under the hood, the resolution algorithm:

1. Handles circular dependencies through cycle detection in the topological sort
2. Supports remapping of requirements to different providers
3. Respects cardinality modifiers on requirements
4. Caches results to avoid redundant processing

## Common Resolution Patterns

The Resource Manager supports several common resolution patterns:

### Feature-Based Resolution

Starting with specific features:

```python
resolver = DepBuilder(
    resources=manager,
    feature_names=["app.web", "feature.analytics"]
)
resolver.resolve()
```

### Remapping-Based Resolution

Using remapping rules to select specific implementations:

```python
resolver = DepBuilder(
    resources=manager,
    feature_names=["app.main"],
    remap_rules={
        "database": "postgres",
        "logging": "file"
    }
)
resolver.resolve()
```

### Custom Resolution Strategies

Implementing custom resolution logic:

```python
class EnvironmentDepBuilder(DepBuilder):
    def __init__(self, environment="development", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environment = environment
    
    def resolve_requirements(self, requirement, lvl=0):
        # Filter providers by environment
        # ...
        
        return super().resolve_requirements(requirement, lvl)
```

## Best Practices

When working with dependency resolution:

1. **Explicit Features**: Always specify the starting features for clarity
2. **Use Remapping**: Use remapping rules instead of hardcoding specific implementations
3. **Avoid Cycles**: Design your resource dependencies to avoid circular references
4. **Test Resolution**: Test your resolution process with different feature combinations
5. **Debug Support**: Enable debug mode to get more information about the resolution process

## Related How-To Guides

For practical examples, see:
- [How to Customize Resource Resolution](../resource_manager_howtos/01_custom_resolution.md)
- [How to Visualize Dependency Graphs](../resource_manager_howtos/06_visualizing_dependencies.md) 