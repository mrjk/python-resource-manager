"""Resource linking and dependency management module.

This module provides classes for managing resource dependencies through provider/requirement 
relationships. It implements a flexible system for defining how resources depend on each other 
and what capabilities they provide to other resources.

The module defines:
- ResourceLink: Base class for resource linking with configuration parsing
- ResourceProviderLink: For capabilities exposed by a resource
- ResourceRequireLink: For dependency requirements with matching logic

Resource links use a rule-based syntax that specifies the kind, instance, and cardinality modifier:
"<kind>.<instance>.<modifier>" where the modifier controls how many matches are required:
- "!" or "one": Exactly one match required
- "?" or "zero_or_one": Zero or one match required
- "+" or "one_or_many": One or more matches required
- "*" or "zero_or_many": Any number of matches allowed
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from resource_manager.binding import (
    BindingTrace,
    match_name_and_providers,
    resolve_binding,
)
from resource_manager.exceptions import (
    ResourceConfigError,
    ResourceLinkError,
    ResourceTypeError,
)

# Resources links implementation
###########################

RESOURCE_LINK_SHORT_MODS = ["!", "?", "*", "+"]
RESOURCE_LINK_LONG_MODS = [
    "one",
    "zero_or_one",
    "zero_or_many",
    "one_or_many",
]
RESOURCE_LINK_MODS = RESOURCE_LINK_SHORT_MODS + RESOURCE_LINK_LONG_MODS


class ResourceLink:
    """Base class for resource linking and dependency management.

    This class provides the core functionality for linking resources together through
    provider/requirement relationships. It parses configuration rules that define how
    resources depend on and provide capabilities to each other.

    Args:
        config (dict): Configuration string or dictionary containing link details:
            - instance (str, optional): Specific instance name for the link
            - kind (str): The type/category of the resource link
            - mod (str, optional): Link modifier specifying cardinality ('!', '?', '*', '+')
                or their long-form equivalents ('one', 'zero_or_one', etc.)
            - raw_value (str, optional): Original unparsed rule string
        parent: The parent resource that owns this link, set to None if not set

    Attributes:
        parent: Reference to parent resource
        instance (str): Instance name for this link
        kind (str): Resource link type/category
        mod (str): Link modifier for cardinality
        raw_value (str): Original rule string if parsed from string format

    The configuration can be provided either as a dictionary or a string rule in the format:
    "<kind>.<instance>.<modifier>" where modifier is optional.
    """

    def __init__(self, config: Dict[str, Any], parent: "Resource" = None):
        self.parent = parent

        config = self.parse_config(config)
        if not isinstance(config, dict):
            raise ResourceTypeError(f"Expected dict, got: {type(config)}={config}")

        self.instance = config.get("instance")
        self.kind = config.get("kind")
        self.mod = config.get("mod", None)
        self.raw_value = config.get("raw_value", None)

        if not self.kind:
            raise ResourceConfigError(f"Kind is required, got: {self.kind}")

        assert isinstance(self.kind, str)
        assert isinstance(self.instance, str) or self.instance is None
        assert isinstance(self.mod, str) or self.mod is None
        assert isinstance(self.raw_value, str) or self.raw_value is None

    def parse_config(
        self, value: Union[str, Dict[str, Any], "ResourceLink"]
    ) -> Dict[str, Any]:
        """Parse the resource link configuration from various input formats.

        This method handles parsing both dictionary configs and string rule formats.
        For string rules, it parses them into the component parts (kind, instance, modifier).

        Args:
            value (Union[str, dict, ResourceLink]): The configuration to parse, can be:
                - String rule in format "<kind>.<instance>.<modifier>"
                - Dictionary with explicit config values
                - Another ResourceLink instance to copy from

        Returns:
            dict: Parsed configuration with standardized keys:
                - kind: Resource type
                - instance: Specific instance name
                - mod: Cardinality modifier
                - raw_value: Original string rule if applicable

        Raises:
            ResourceConfigError: If the string rule format is invalid
            ResourceTypeError: If the input type is not supported
        """
        if isinstance(value, str):
            value = ResourceLink.parse_str_config(value)
        elif isinstance(value, self.__class__):
            value = ResourceLink.parse_obj_config(value)

        # Ensure we always provide correct type
        if not isinstance(value, dict):
            raise ResourceTypeError(f"Invalid value type: {type(value)}={value}")

        return value

    @staticmethod
    def parse_str_config(raw_value: str) -> Dict[str, Any]:
        """Parse a string rule into a configuration dictionary.

        Args:
            raw_value (str): String rule in format "<kind>.<instance>.<modifier>"

        Returns:
            dict: Parsed configuration dictionary

        Raises:
            ResourceConfigError: If the string rule format is invalid
        """
        parts = raw_value.split(".")

        # Start to test last part if is a modifier or not
        mod = None
        if parts[-1] in RESOURCE_LINK_SHORT_MODS:
            mod = parts[-1]
            parts = parts[:-1]

        if len(parts) == 1:
            value = {
                "kind": parts[0],
                "instance": None,
            }
        elif len(parts) == 2:
            value = {
                "kind": parts[0],
                "instance": parts[1],
            }
        else:
            raise ResourceConfigError(f"Invalid provider rule: {raw_value}")

        # Save raw value
        value["mod"] = mod
        value["raw_value"] = raw_value

        return value

    @staticmethod
    def parse_obj_config(obj: "ResourceLink") -> Dict[str, Any]:
        """Copy configuration from another ResourceLink object.

        Args:
            obj (ResourceLink): The ResourceLink object to copy from

        Returns:
            dict: Configuration dictionary copied from the object
        """
        value = {}
        value["kind"] = obj.kind
        value["instance"] = obj.instance
        value["mod"] = obj.mod
        value["raw_value"] = obj.raw_value
        return value

    @property
    def rule(self) -> str:
        """Generate the canonical rule string for this resource link.

        Returns:
            str: Rule string in format "<kind>.<instance>" or "<kind>.*" if no instance
        """
        out = [self.kind]
        out.append(self.instance or "ANY")
        out.append(self.mod or "DEFAULT")
        return ".".join(out)

    @property
    def resource(self) -> "Resource":
        """Get the parent resource that owns this link.

        Returns:
            Resource: The parent resource instance
        """
        return self.parent

    def __repr__(self):
        if self.resource is None:
            return f"{self.__class__.__name__}({self.rule})"
        return f"{self.__class__.__name__}({self.rule})[{self.resource.name}]"


class ResourceProviderLink(ResourceLink):
    """Resource provider link that represents a capability exposed by a resource.

    This class extends ResourceLink to specifically handle provider links, which define
    what capabilities or features a resource makes available to other resources.
    """


class ResourceRequireLink(ResourceLink):
    """Resource require link that represents a dependency requirement.

    This class extends ResourceLink to handle requirement links, which define what
    capabilities a resource needs from other resources to function. It includes
    sophisticated matching and validation logic to find compatible providers.

    Attributes:
        default_providers_name (str): Default name to use for providers when not specified
        default_requirement_name (str): Default name to use for requirement when not specified.
            Only used by match_provider method if remap_requirement is True.

    The matching process supports various cardinality modifiers:
        - "!" or "one": Exactly one match required
        - "?" or "zero_or_one": Zero or one match required
        - "+" or "one_or_many": One or more matches required
        - "*" or "zero_or_many": Any number of matches allowed
    """

    default_providers_name: str = "default"
    default_requirement_name: str = "default"

    def match_provider(
        self,
        providerlinks: List[ResourceProviderLink],
        remap_rules: Optional[Dict[str, Optional[str]]] = None,
        default_mode: str = "one",
        remap_requirement: bool = True,
    ) -> Tuple[Optional[str], List[ResourceProviderLink]]:
        """Match this requirement against providers (compat wrapper).

        Prefer :meth:`match_provider_traced` when the caller needs binding
        reason / candidates. Precedence is pin > remap > default_alias > schema.
        Remap value ``NONE`` / ``None`` unbinds the kind (no invented `.default`).
        """
        trace = self.match_provider_traced(
            providerlinks,
            remap_rules=remap_rules,
            default_mode=default_mode,
            remap_requirement=remap_requirement,
        )
        return match_name_and_providers(trace)

    def match_provider_traced(
        self,
        providerlinks: List[ResourceProviderLink],
        remap_rules: Optional[Dict[str, Optional[str]]] = None,
        default_mode: str = "one",
        remap_requirement: bool = True,
    ) -> BindingTrace:
        """Match providers and return an explainable :class:`BindingTrace`."""
        trace = resolve_binding(
            self,
            providerlinks,
            remap_rules=remap_rules,
            default_mode=default_mode,
            default_instance_name=self.default_requirement_name,
            remap_requirement=remap_requirement,
        )
        self._validate_binding(trace, providerlinks)
        return trace

    def _validate_binding(
        self,
        trace: BindingTrace,
        providerlinks: List[ResourceProviderLink],
    ) -> None:
        """Validate cardinality; attach *trace* on :class:`ResourceLinkError`."""
        mod = trace.requirement_mod
        if mod not in RESOURCE_LINK_MODS:
            raise ResourceConfigError(f"Invalid mod: {mod}")

        matches = trace.matches
        requirement_name = trace.resolved_instance

        def build_error_info():
            choices = [link for link in providerlinks if link.kind == self.kind]
            choices_names = (
                " ".join(
                    [
                        f"{link.instance}" if link.instance is not None else "default"
                        for link in choices
                    ]
                )
                or "<NO OTHER CHOICES>"
            )
            if requirement_name is not None and self.instance is None:
                msg_suffix = f" ({requirement_name})"
            elif trace.reason == "unbound":
                msg_suffix = " (unbound/NONE)"
            elif trace.reason == "schema":
                msg_suffix = " (schema)"
            else:
                msg_suffix = ""
            rule_ident = f"{self.rule}{msg_suffix}"
            return rule_ident, choices_names

        def raise_link_error(msg: str) -> None:
            raise ResourceLinkError(msg, binding_trace=trace)

        if mod in ["!", "one"]:
            if not len(matches) == 1:
                rule_ident, choices_names = build_error_info()
                msg = (
                    f"Requirement {rule_ident} did not match exactly one provider, "
                    f"got: {len(matches)}, reason={trace.reason}, "
                    f"please chose one of: {choices_names}"
                )
                raise_link_error(msg)
        if mod in ["?", "zero_or_one"]:
            if not len(matches) < 2:
                rule_ident, choices_names = build_error_info()
                msg = (
                    f"Requirement {rule_ident} did not match exactly zero or one provider, "
                    f"got: {len(matches)}, reason={trace.reason}, "
                    f"please chose one of: {choices_names}"
                )
                raise_link_error(msg)
        if mod in ["+", "one_or_many"]:
            if not len(matches) >= 1:
                rule_ident, choices_names = build_error_info()
                msg = (
                    f"Requirement {rule_ident} did not match one or more providers, "
                    f"got: {len(matches)}, reason={trace.reason}, "
                    f"please chose one of: {choices_names}"
                )
                raise_link_error(msg)
