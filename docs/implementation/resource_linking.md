# Resource Linking

This document explains how resource linking works in the Resource Manager, detailing the mechanism that connects resources through their provides/requires relationships.

## Link Structure

The resource linking system consists of several key classes:

### ResourceLink

The base class for all resource links, with common properties:

- **kind**: The capability or requirement category (e.g., "database")
- **instance**: An optional specific identifier (e.g., "postgres")
- **resource**: The resource that owns this link

The string format for a link is `kind.instance`, with the instance being optional.

### ResourceProviderLink

Represents a capability that a resource provides:

```python
class ResourceProviderLink(ResourceLink):
    def __init__(self, kind, instance=None, resource=None):
        super().__init__(kind, instance, resource)
```

### ResourceRequireLink

Represents a dependency that a resource requires:

```python
class ResourceRequireLink(ResourceLink):
    def __init__(self, kind, instance=None, resource=None, mod=None):
        super().__init__(kind, instance, resource)
        self.mod = mod or "!"  # Default is required (exactly one)
```

The `mod` attribute controls cardinality:
- `!` (one): Exactly one provider required (default)
- `?` (zero_or_one): Zero or one provider allowed
- `+` (one_or_many): One or more providers required
- `*` (zero_or_many): Any number of providers allowed, including none

## Link Parsing

The Resource Manager parses link strings into link objects:

```python
def parse_provider_link(provider_str, resource=None):
    """Parse a provider link string into a ResourceProviderLink."""
    parts = provider_str.split(".")
    
    if len(parts) == 1:
        # Just a kind with no instance
        return ResourceProviderLink(parts[0], resource=resource)
    else:
        # Has both kind and instance
        kind = parts[0]
        instance = ".".join(parts[1:])
        return ResourceProviderLink(kind, instance, resource)

def parse_require_link(require_str, resource=None):
    """Parse a requirement link string into a ResourceRequireLink."""
    # Check for modifiers
    mod = None
    if require_str.endswith("?"):
        mod = "?"
        require_str = require_str[:-1]
    elif require_str.endswith("*"):
        mod = "*"
        require_str = require_str[:-1]
    elif require_str.endswith("+"):
        mod = "+"
        require_str = require_str[:-1]
    elif require_str.endswith("!"):
        mod = "!"
        require_str = require_str[:-1]
    
    # Parse parts
    parts = require_str.split(".")
    
    if len(parts) == 1:
        # Just a kind with no instance
        return ResourceRequireLink(parts[0], mod=mod, resource=resource)
    else:
        # Has both kind and instance
        kind = parts[0]
        instance = ".".join(parts[1:])
        return ResourceRequireLink(kind, instance, resource, mod)
```

## Link Management

The Resource class manages links through several methods:

### Adding Links

```python
def add_provider(self, provider):
    """Add a capability that this resource provides."""
    if isinstance(provider, str):
        provider = parse_provider_link(provider, self)
    
    self.provider_links.append(provider)
    return provider

def add_requirement(self, requirement):
    """Add a dependency that this resource requires."""
    if isinstance(requirement, str):
        requirement = parse_require_link(requirement, self)
    
    self.require_links.append(requirement)
    return requirement
```

### Accessing Links

```python
def get_provider_links(self, kind=None):
    """Get provider links, optionally filtered by kind."""
    if kind is None:
        return self.provider_links
    
    return [p for p in self.provider_links if p.kind == kind]

def get_requirement_links(self, kind=None):
    """Get requirement links, optionally filtered by kind."""
    if kind is None:
        return self.require_links
    
    return [r for r in self.require_links if r.kind == kind]
```

## Link Matching

During dependency resolution, requirement links are matched with provider links:

```python
def match_provider(self, provider_links, remap_rules=None, default_mode="one", remap_requirement=False):
    """Match this requirement with compatible providers."""
    # Apply remapping if available
    requirement = self
    if remap_requirement and remap_rules and self.kind in remap_rules:
        # Create a new requirement with remapped kind
        remapped_kind = remap_rules[self.kind]
        requirement = ResourceRequireLink(remapped_kind, self.instance, self.resource, self.mod)
    
    # Find matching providers by kind
    matches = [p for p in provider_links if p.kind == requirement.kind]
    
    # If instance is specified, filter by it
    if requirement.instance:
        instance_matches = [p for p in matches if p.instance == requirement.instance]
        if instance_matches:
            matches = instance_matches
    
    # Determine match name
    match_name = requirement.instance or "default"
    
    # Return based on cardinality
    mode = requirement.mod or default_mode
    
    if mode in ["!", "one"]:
        # Exactly one required
        if not matches:
            raise ValueError(f"No provider found for required dependency {requirement}")
        if len(matches) > 1:
            raise ValueError(f"Multiple providers found for dependency {requirement} that requires exactly one")
        return match_name, matches
    
    elif mode in ["?", "zero_or_one"]:
        # Zero or one allowed
        if len(matches) > 1:
            raise ValueError(f"Multiple providers found for dependency {requirement} that allows at most one")
        return match_name, matches
    
    elif mode in ["+", "one_or_many"]:
        # One or more required
        if not matches:
            raise ValueError(f"No provider found for required dependency {requirement} that requires at least one")
        return match_name, matches
    
    elif mode in ["*", "zero_or_many"]:
        # Any number allowed
        return match_name, matches
    
    else:
        raise ValueError(f"Unsupported requirement mode: {mode}")
```

## Edge Links

During resolution, matched requirements and providers are connected through `EdgeLink` objects:

```python
class EdgeLink:
    """Represents a connection between a requirement and provider."""
    
    def __init__(self, requirement, provider, match_name):
        self.requirement = requirement
        self.provider = provider
        self.match_name = match_name
```

The dependency tree consists of a dictionary mapping resource names to lists of EdgeLinks.

## Implementation Details

Under the hood, the linking system:

1. Maintains the raw links in `provider_links` and `require_links` lists
2. Automatically parses string-based links into objects
3. Ensures link objects reference their owner resources
4. Provides matching logic for dependency resolution

## Remapping Rules

The linking system supports remapping rules, which allow requirements to be redirected to different providers:

```python
# Example remapping rules
remap_rules = {
    "database": "postgres",  # Remap generic "database" to specific "postgres"
    "logging": "file"        # Remap generic "logging" to specific "file"
}
```

When resolving dependencies, the resolver applies these rules before matching.

## Best Practices

When working with resource links:

1. **Consistent Naming**: Use a consistent convention for kinds and instances
2. **Explicit Cardinality**: Always specify cardinality modifiers for clarity
3. **Generic Requirements**: For flexibility, use generic requirements (e.g., "database") and remap them later
4. **Avoid Ambiguity**: Avoid configurations that lead to ambiguous matching

## Related How-To Guides

For practical examples, see:
- [How to Customize Resource Resolution](../resource_manager_howtos/01_custom_resolution.md)
- [How to Handle Optional Dependencies](../resource_manager_howtos/04_optional_dependencies.md) 