"""Binding selection: precedence, remaps, and explainable traces.

Selection precedence (highest wins):

    pin  >  remap  >  default_alias  >  schema

Remap sentinel ``NONE`` (or ``None``) unbinds a kind: do not invent a
``.default`` instance. Optional requirements (``?``, ``*``) may then resolve
to zero providers; singular ``!`` / ``+`` still fail with a clear trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

if TYPE_CHECKING:
    from resource_manager.links import ResourceProviderLink, ResourceRequireLink

# Remap value that disables default/instance selection for a kind.
REMAP_NONE = "NONE"

BindingReason = str  # pin | remap | default_alias | schema | unbound


def is_remap_none(value: object) -> bool:
    """Return True if *value* is the unbind sentinel."""
    if value is None:
        return True
    if isinstance(value, str) and value.upper() == REMAP_NONE:
        return True
    return False


def effective_provider_instance(
    provider: "ResourceProviderLink",
    *,
    default_name: str = "default",
) -> str:
    """Normalize a provider's instance name for comparison."""
    if provider.instance is None:
        return default_name
    return provider.instance


@dataclass
class BindingTrace:
    """Explainable result of matching one requirement to providers."""

    kind: str
    reason: BindingReason
    resolved_instance: Optional[str]
    matches: List["ResourceProviderLink"] = field(default_factory=list)
    candidates: List["ResourceProviderLink"] = field(default_factory=list)
    requirement_instance: Optional[str] = None
    requirement_mod: Optional[str] = None
    requirement_raw: Optional[str] = None
    consumer: Optional[str] = None
    remap_value: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        """JSON-friendly summary for inspect / CLI."""
        return {
            "kind": self.kind,
            "reason": self.reason,
            "resolved_instance": self.resolved_instance,
            "requirement_instance": self.requirement_instance,
            "requirement_mod": self.requirement_mod,
            "requirement_raw": self.requirement_raw,
            "consumer": self.consumer,
            "remap_value": self.remap_value,
            "matches": [
                {
                    "kind": link.kind,
                    "instance": link.instance,
                    "resource": link.resource.name if link.resource else None,
                }
                for link in self.matches
            ],
            "candidates": [
                {
                    "kind": link.kind,
                    "instance": link.instance,
                    "resource": link.resource.name if link.resource else None,
                }
                for link in self.candidates
            ],
        }


def resolve_binding(
    requirement: "ResourceRequireLink",
    providerlinks: Sequence["ResourceProviderLink"],
    remap_rules: Optional[Dict[str, Optional[str]]] = None,
    *,
    default_mode: str = "one",
    default_instance_name: str = "default",
    remap_requirement: bool = True,
) -> BindingTrace:
    """Match *requirement* to providers and record why.

    When ``remap_requirement`` is False, behave like legacy kind-only matching
    (no pin/remap/default pipeline): all providers of the same kind match when
    the requirement has no instance.
    """
    # Local import avoids circular import at module load.
    # pylint: disable=import-outside-toplevel
    from resource_manager.exceptions import ResourceTypeError

    remap_rules = remap_rules or {}
    if not isinstance(remap_rules, dict):
        raise ResourceTypeError(
            f"Expected dict for remap_rules, got: {type(remap_rules)}"
        )

    mod = requirement.mod or default_mode
    consumer = (
        requirement.resource.name
        if requirement.resource is not None
        else None
    )
    candidates = [p for p in providerlinks if p.kind == requirement.kind]

    if not remap_requirement:
        return _legacy_kind_match(
            requirement,
            candidates,
            mod=mod,
            consumer=consumer,
            default_instance_name=default_instance_name,
        )

    # --- Precedence: pin > remap > default_alias > schema ---
    reason: BindingReason
    resolved: Optional[str]
    matches: List["ResourceProviderLink"]
    remap_value: Optional[str] = None

    if requirement.instance is not None:
        reason = "pin"
        resolved = requirement.instance
        matches = _match_instance(candidates, resolved, default_instance_name)
    elif requirement.kind in remap_rules:
        remap_value = remap_rules[requirement.kind]
        if is_remap_none(remap_value):
            reason = "unbound"
            resolved = None
            matches = []
            remap_value = REMAP_NONE
        else:
            if not isinstance(remap_value, str):
                raise ResourceTypeError(
                    f"Requirement name must be a string, got: {type(remap_value)}"
                )
            reason = "remap"
            resolved = remap_value
            matches = _match_instance(candidates, resolved, default_instance_name)
    else:
        default_matches = _match_instance(
            candidates, default_instance_name, default_instance_name
        )
        if default_matches:
            reason = "default_alias"
            resolved = default_instance_name
            matches = default_matches
        else:
            reason = "schema"
            resolved = None
            matches = list(candidates)

    trace = BindingTrace(
        kind=requirement.kind,
        reason=reason,
        resolved_instance=resolved,
        matches=matches,
        candidates=list(candidates),
        requirement_instance=requirement.instance,
        requirement_mod=mod,
        requirement_raw=requirement.raw_value,
        consumer=consumer,
        remap_value=remap_value if isinstance(remap_value, str) else None,
    )
    return trace


def _match_instance(
    candidates: Sequence["ResourceProviderLink"],
    instance_name: str,
    default_name: str,
) -> List["ResourceProviderLink"]:
    return [
        p
        for p in candidates
        if effective_provider_instance(p, default_name=default_name) == instance_name
    ]


def _legacy_kind_match(
    requirement: "ResourceRequireLink",
    candidates: Sequence["ResourceProviderLink"],
    *,
    mod: str,
    consumer: Optional[str],
    default_instance_name: str,
) -> BindingTrace:
    """Legacy ``remap_requirement=False``: kind filter, optional instance pin."""
    if requirement.instance is None:
        matches = list(candidates)
        reason: BindingReason = "schema"
        resolved: Optional[str] = None
    else:
        matches = _match_instance(
            candidates, requirement.instance, default_instance_name
        )
        reason = "pin"
        resolved = requirement.instance

    return BindingTrace(
        kind=requirement.kind,
        reason=reason,
        resolved_instance=resolved,
        matches=matches,
        candidates=list(candidates),
        requirement_instance=requirement.instance,
        requirement_mod=mod,
        requirement_raw=requirement.raw_value,
        consumer=consumer,
        remap_value=None,
    )


def match_name_and_providers(
    trace: BindingTrace,
) -> Tuple[Optional[str], List["ResourceProviderLink"]]:
    """Compat tuple used by existing ``match_provider`` / DepBuilder callers."""
    return trace.resolved_instance, list(trace.matches)
