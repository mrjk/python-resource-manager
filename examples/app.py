import sys
from pprint import pprint
from datetime import datetime

# import networkx as nx
# from collections import defaultdict
# from types import SimpleNamespace

import logging

# from graphlib import TopologicalSorter
import pydot


# from examples.model import (
#     Catalog,
#     # App,
#     GlobalCfg,
#     # ContextFeature,
#     # ProvideLink,
#     # RequireLink,
# )

from resource_manager.resources import ResourceManager, Resource
from resource_manager.resolver import DepBuilder
# from resource_manager.links import ResourceLinkError


logger = logging.getLogger(__name__)


# Resource manager overrides


class PaasifyResource(Resource):
    "Paasify resource"

    default_attrs = {
        "desc": None,
        "group": None,
        "vars": {},
    }


class PaasifyResourceManager(ResourceManager):
    "Paasify resource manager"

    resource_class = PaasifyResource


# App management
###################################



class AppBase:
    "Simple object to work with apps"

    def __init__(
        self,
        app_name,
        app_config,
        feature_names=None,
        remap_rules=None,
    ):
        self.app_name = app_name
        self.app_config = app_config
        # TOFIX: We expect a dict or something else here
        print("APP CONFIG", type(self.app_config))

        self.rmanager = PaasifyResourceManager()
        self.rmanager.add_resources(self.app_config.features.get_value(), scope="app")

        # Build feature names
        self.feature_names = self.get_features(feature_names)

        # Prepare build context
        self.remap_rules = self.get_remap_rules(remap_rules)


    def dump(self):
        "Dump app App context"

        print("-------------- Debug - Start ------------------")
        print("Object:", self)
        print("App Name:", self.app_name)
        print("Resource Manager:", self.rmanager)
        print("App Config:", type(self.app_config))
        print("Feature Names:")
        pprint(self.feature_names)
        print("Remap Rules:")
        pprint(self.remap_rules)
        print("--------------  Debug - End  ------------------")


    def get_features(self, feature_names: list = None) -> list:
        """Return a list of feature requirements from list of feature names.

        Args:
            feature_names (list): List of feature names. Prepend with ! or ~ to exclude
                                  features enabled by default.


        Returns:
            list: List of feature requirements
        """

        # Process requested features and base features
        feature_names = feature_names or []
        assert isinstance(
            feature_names, list
        ), f"Expected list of strings, got: {type(feature_names)}={feature_names}"
        feature_names.extend(self.app_config.default_features)


        # Exclude features
        excluded_features = []
        enabled_features = []
        for name in feature_names:
            if name.startswith("!") or name.startswith("~"):
                excluded_features.append(name[1:])
            else:
                enabled_features.append(name)
        enabled_features = [x for x in enabled_features if x not in excluded_features]
        logger.debug("Enabled features: %s", enabled_features)
        logger.debug("Excluded features: %s", excluded_features)

        # Ensure features are correctly prefixed
        feature_names = [
            f"feature.{x}" if not x.startswith("feature.") else x
            for x in enabled_features
        ]

        # Auto __base__ feature if not present
        if not "feature.__base__" in feature_names:
            feature_names.insert(0, "feature.__base__")

        # Remove duplicates features and save result
        return list(set(feature_names))

    def get_remap_rules(self, remap_rules: dict = None) -> dict:
        "Return remap rules"

        remap_rules = remap_rules or {}
        assert isinstance(remap_rules, dict)

        remap_rules = {}
        remap_rules.update(self.app_config.remap_rules)
        remap_rules.update(remap_rules)
        return remap_rules

    def dump_app(self, full=True, dump=False):
        "Dump app from catalog"

        app = self.app_config

        # Return dump if requested
        if dump:
            app_dump = dict(app.get_value())
            if not full:
                del app_dump["features"]

            pprint(app_dump)
            return app_dump

        print("-------------- Debug - Start ------------------")

        # Return print status
        print("\n\nApp:", app)
        print("  Default features:", app.default_features)
        print("  Resource model:", app.resource_model)

        print("  Features:", len(app.features))
        print("--------------  Debug - End  ------------------")
        if not full:
            return

        # for res_link in app.features:
        #     print(f"\n   {res_link.key}: {res_link.desc}")
        #     print(f"     group: {res_link.group}")
        #     print(f"     group_mode: {res_link.group_mode}")
        #     print(f"     group_default: {res_link.group_default}")

        #     if res_link.provides:
        #         print(f"     provides: {len(res_link.provides)}")
        #         for requirement in res_link.provides:
        #             print(
        #                 f"     - {requirement.rule}",
        #             )

        #     if res_link.requires:
        #         print(f"     requires: {len(res_link.requires)}")
        #         for requirement in res_link.requires:
        #             print(
        #                 f"     - {requirement.rule}",
        #             )


# Dependency resolvers
###################################


class FeatureDepBuilder(DepBuilder):
    "Dependency builder for features"

    resource_manager_class: ResourceManager = PaasifyResourceManager

    def _resolve(self):
        "Resolve driver"
        # Resolve tree
        self.provider_links = self._build_provider_links()
        self.dep_tree = self._get_dependencies(debug=self.debug)

        self.dep_topo = self._get_simplified_tree(self.dep_tree)
        self.dep_order = self._get_dependencies_order(self.dep_topo)

    def resolve_requirements(self, requirement, lvl=0):
        """Resolve requirements for features.

        Args:
            requirement (ResourceRequireLink): The requirement to resolve
            lvl (int, optional): Current recursion level. Defaults to 0.

        Returns:
            tuple: A tuple containing:
                - str: The resolved requirement name after any remapping
                - list: List of ResourceProviderLink objects that satisfy this requirement
        """

        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )

        return match_name, provider_links


# class PluginDepBuilder(DepBuilder):
#     "Dependency builder for plugins"

#     resource_manager_class: ResourceManager = PaasifyResourceManager

#     def _resolve(self):
#         "Resolve driver"
#         # Resolve tree
#         self.provider_links = self._build_provider_links()
#         self.dep_tree = self._get_dependencies(debug=self.debug)

#     def resolve_requirements(self, requirement, lvl=0):
#         """Resolver for plugins.

#         Args:
#             requirement (ResourceRequireLink): The requirement to resolve
#             lvl (int, optional): Current recursion level. Defaults to 0.

#         Returns:
#             tuple: A tuple containing:
#                 - str: The resolved requirement name after any remapping
#                 - list: List of ResourceProviderLink objects that satisfy this requirement
#         """

#         try:
#             match_name, provider_links = requirement.match_provider(
#                 self.provider_links,
#                 remap_rules=self.remap_rules,
#                 default_mode="one_or_many",
#                 remap_requirement=False,
#             )
#         except ResourceLinkError as err:
#             print(f"Skip plugin since: {err}")
#             match_name = None
#             provider_links = []

#         return match_name, provider_links


# App resolver
###################################


class AppResolver(AppBase):
    "Resolver for a given app"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.builder = None

    def resolve(
        self,
        extra_resources=None,
        extra_plugins=None,
        sources=None,
        resolve_features=True,
    ):
        "Resolve resources and plugins"

        # Prepare arguments
        extra_resources = extra_resources or {}
        extra_plugins = extra_plugins or {}
        sources = tuple(sources or ("catalog", "context"))

        # Overview graphs only need resources loaded; skip feature walk so
        # partial sources (catalog-only / context-only) do not fail on missing providers.
        if resolve_features and "catalog" in sources:
            feature_names = self.feature_names
        else:
            feature_names = []

        # Prepare resources builder
        builder = FeatureDepBuilder(
            # resources=self.rmanager.copy(),
            remap_rules=self.remap_rules,
            feature_names=feature_names,
        )

        if "catalog" in sources:
            out = self.rmanager.dump_catalog()
            builder.add_resources(out, scope="app_resources")
        if "context" in sources:
            builder.add_resources(extra_resources, scope="context_resources")

        builder.resolve()

        # print("Resource resolution for app: %s", self.app_name)
        # print("  > RESOURCE DEP TREE:")
        # pprint(builder.dep_tree)
        # print("  > RESOURCE DEP TOPO:")
        # pprint(builder.dep_topo)
        # print("  > RESOURCE DEP ORDER:")
        # pprint(builder.dep_order)

        # Save pod results
        self.builder = builder

        return

        # Then resolve plugins
        print("\n\n\n\nRESOLVE PLUSINGS")
        # pprint(self.app_config.plugins.get_value())
        enabled_resources = {
            key: builder.rmanager.get_resource(key) for key in builder.dep_order
        }
        # pprint(enabled_resources)
        # assert False

        # Plugins to be implemented

        plugin_builder = PluginDepBuilder(
            remap_rules=self.remap_rules,
            feature_names=["plugin"],
        )
        plugin_builder.add_resources(enabled_resources, scope="app_resources")
        plugin_builder.add_resources(
            self.app_config.plugins.get_value(), scope="app_plugins"
        )

        print("Plugin resolution for app: %s", self.app_name)
        plugin_builder.resolve()

        # pprint(plugin_builder.__dict__)

        # print("  > PLUGIN DEP TREE:")
        # pprint(plugin_builder.dep_tree)
        # print("  > PLUGIN DEP TOPO:")
        # pprint(plugin_builder.dep_topo)
        # print("  > PLUGIN DEP ORDER:")
        # pprint(plugin_builder.dep_order)

        # plugin_builder.add_resources(extra_plugins, scope="context_plugins")
        # plugin_builder.resolve_resources()
        # builder_plugins = DepBuilder(
        #     remap_rules=self.remap_rules,
        #     feature_names=self.feature_names,
        # )

    # Public API
    # ===============

    def gen_all_resources_graph(
        self,
        output_file="output.png",
        show_provides=False,
        show_vars=False,
    ):
        "Generate a graph of all resources with requires/provides links"

        resources_catalog = self.builder.rmanager
        hidden_nodes = {self.builder.root_node_name, "__root__", "__builder__"}

        # All declared provides in the catalog (not the contextualized resolution)
        provider_links = [
            provide
            for resource in resources_catalog.catalog.values()
            for provide in resource.provides
            if resource.name not in hidden_nodes
        ]

        # Create a root directed graph
        console_font = "Courier"
        graph = pydot.Dot(
            "my_graph",
            layout="dot",
            rankdir="LR",
            graph_type="digraph",
            newrank=True,
            bgcolor="white",
            label=f"{self.app_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            labelloc="t",
            fontname=console_font,
            ranksep="1.8",
            nodesep="0.6",
        )

        # Node styles by group (shared with legend)
        group_styles = [
            {"color": "black", "fillcolor": "lightgreen", "shape": "box", "legend": "App resource", "key": "app"},
            {"color": "blue", "fillcolor": "lightblue", "shape": "box", "legend": "Global resource", "key": "global"},
            {
                "color": "red",
                "fillcolor": "#ffcccc",
                "shape": "cds",
                "legend": "Base feature (requested)",
                "key": "base_requested",
            },
            {
                "color": "purple",
                "fillcolor": "#e0c0ff",
                "shape": "cds",
                "legend": "Base feature",
                "key": "base",
            },
            {
                "color": "green",
                "fillcolor": "#ccffcc",
                "shape": "box",
                "legend": "Internal resource",
                "key": "internal",
            },
        ]
        styles_by_key = {s["key"]: s for s in group_styles}

        # Edge styles by require modifier.
        # Unset mod (None) means "one" at resolve time (DepBuilder default_mode="one").
        one_style = {
            "color": "#555555",
            "penwidth": "2.5",
            "legend": "one (! or default) — exactly one",
        }
        edge_styles = {
            "!": one_style,
            "one": one_style,
            None: one_style,
            "?": {
                "color": "#e67e22",
                "style": "dashed",
                "penwidth": "2.5",
                "legend": "zero_or_one (?) — optional",
            },
            "zero_or_one": {
                "color": "#e67e22",
                "style": "dashed",
                "penwidth": "2.5",
                "legend": "zero_or_one (?) — optional",
            },
            "+": {
                "color": "#27ae60",
                "penwidth": "2.5",
                "legend": "one_or_many (+) — one or more",
            },
            "one_or_many": {
                "color": "#27ae60",
                "penwidth": "2.5",
                "legend": "one_or_many (+) — one or more",
            },
            "*": {
                "color": "#8e44ad",
                "style": "dashed",
                "penwidth": "2.5",
                "legend": "zero_or_many (*) — any count",
            },
            "zero_or_many": {
                "color": "#8e44ad",
                "style": "dashed",
                "penwidth": "2.5",
                "legend": "zero_or_many (*) — any count",
            },
        }
        # Unique legend rows (short mods only, avoid duplicate long-form)
        edge_legend = [
            one_style,
            edge_styles["?"],
            edge_styles["+"],
            edge_styles["*"],
        ]

        def style_for_resource(resource):
            if resource.group == "__global__":
                return styles_by_key["global"]
            if resource.group == "__base__":
                if f"feature.{resource.name}" in self.feature_names:
                    return styles_by_key["base_requested"]
                return styles_by_key["base"]
            if resource.group == "__internal__":
                return styles_by_key["internal"]
            return styles_by_key["app"]

        # Legend (HTML table stays readable with rankdir=LR)
        legend_rows = [
            '<TR><TD COLSPAN="2" ALIGN="CENTER"><B>Legend</B></TD></TR>',
            '<TR><TD COLSPAN="2" ALIGN="LEFT">Arrow: requires → provides</TD></TR>',
            '<TR><TD COLSPAN="2" ALIGN="CENTER"><B>Resources</B></TD></TR>',
        ]
        for style in group_styles:
            legend_rows.append(
                f'<TR><TD COLSPAN="2" BGCOLOR="{style["fillcolor"]}" BORDER="1">'
                f'{style["legend"]}</TD></TR>'
            )
        legend_rows.append(
            '<TR><TD COLSPAN="2" ALIGN="CENTER"><B>Link modifiers</B></TD></TR>'
        )
        for style in edge_legend:
            legend_rows.append(
                f'<TR><TD BGCOLOR="{style["color"]}" WIDTH="20"> </TD>'
                f'<TD ALIGN="LEFT">{style["legend"]}</TD></TR>'
            )
        legend_html = (
            '<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            + "".join(legend_rows)
            + "</TABLE>>"
        )
        graph.add_node(
            pydot.Node(
                "legend",
                shape="plaintext",
                label=legend_html,
                fontname=console_font,
            )
        )

        # Add nodes for each resource (group = fill color, no clusters)
        for resource_name, resource in resources_catalog.catalog.items():
            if resource_name in hidden_nodes:
                continue

            var_list = [f"{k}: {v}" for k, v in resource.vars.items()]
            style = style_for_resource(resource)

            rows = [f'<TR><TD ALIGN="LEFT"><B>{resource_name}</B></TD></TR>']
            if show_provides and resource.provides:
                for provide in resource.provides:
                    parts = [provide.kind]
                    if provide.instance:
                        parts.append(provide.instance)
                    if provide.mod:
                        parts.append(provide.mod)
                    rows.append(
                        f'<TR><TD ALIGN="LEFT">'
                        f'<FONT POINT-SIZE="9" COLOR="#666666">'
                        f"• {'.'.join(parts)}"
                        f"</FONT></TD></TR>"
                    )
            if show_vars and var_list:
                rows.append(
                    '<TR><TD ALIGN="LEFT">'
                    '<FONT POINT-SIZE="9" COLOR="#666666"><I>vars:</I></FONT>'
                    "</TD></TR>"
                )
                for var_line in var_list:
                    rows.append(
                        f'<TR><TD ALIGN="LEFT">'
                        f'<FONT POINT-SIZE="9" COLOR="#666666">{var_line}</FONT>'
                        "</TD></TR>"
                    )
            label = (
                '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" '
                'CELLPADDING="1" ALIGN="LEFT">'
                + "".join(rows)
                + "</TABLE>>"
            )

            node = pydot.Node(
                resource_name,
                shape=style["shape"],
                color=style["color"],
                style="filled",
                fillcolor=style["fillcolor"],
                label=label,
                fontname=console_font,
                labeljust="l",
                labelloc="c",
                nojustify=True,
                margin="0.15,0.1",
            )
            graph.add_node(node)

        # Add edges for all declared requires/provides (kind match only, no remap)
        for resource_name, resource in resources_catalog.catalog.items():
            if resource_name in hidden_nodes:
                continue
            for requirement in resource.requires:
                for provider in provider_links:
                    # Same kind rules as match_provider, without instance remapping
                    kind_match = provider.kind == requirement.kind or (
                        provider.parent is not None
                        and provider.parent.name == requirement.kind
                    )
                    if not kind_match:
                        continue
                    provider_name = provider.resource.name
                    if provider_name == resource_name or provider_name in hidden_nodes:
                        continue
                    label = requirement.rule
                    edge_style = edge_styles.get(
                        requirement.mod, edge_styles[None]
                    )
                    # Arrow: requirer → provider (points to what is required)
                    edge_kwargs = {
                        "label": label,
                        "fontcolor": "lightgrey",
                        "fontname": console_font,
                        "color": edge_style["color"],
                    }
                    if edge_style.get("style"):
                        edge_kwargs["style"] = edge_style["style"]
                    if edge_style.get("penwidth"):
                        edge_kwargs["penwidth"] = edge_style["penwidth"]
                    edge = pydot.Edge(
                        resource_name,
                        provider_name,
                        **edge_kwargs,
                    )
                    graph.add_edge(edge)

        graph.write_png(output_file)


    def gen_graph_raw(self, output_file="output.png"):
        "Generate a graph of the app dependencies"

        self.builder.gen_graph(output_file)
        

    def gen_graph(self, output_file="output.png"):
        "Generate a graph of the app dependencies"

        # resources_catalog = self.rmanager
        # dep_tree = self.dep_tree
        resources_catalog = self.builder.rmanager
        dep_tree = self.builder.dep_tree
        process_order = self.builder.dep_order

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

        # Create container subgraphs
        cluster_app = pydot.Cluster(
            "cluster_app",
            label=f"{self.app_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            # rank="same",
            #   color="black",
            #   style="filled",
            #   fillcolor="lightblue"
            newrank=True,
            rankdir="TB",
            style="filled",
            fillcolor="lightgreen",
        )
        cluster_global = pydot.Cluster(
            "cluster_global",
            label="Global",
            # rank="min",
            newrank=True,
            rankdir="TB",
            style="filled",
            fillcolor="lightblue",
        )

        graph.add_subgraph(cluster_app)
        graph.add_subgraph(cluster_global)

        # Add nodes for each resource
        for resource_name in process_order:
            resource = resources_catalog.get_resource(resource_name)

            var_list = [f"{k}: {v}" for k, v in resource.vars.items()]
            var_str = "\n".join(var_list)

            dest = cluster_app
            color = "black"
            shape = "box"
            rank = "same"
            label = f"\\N\n{var_str}\l"
            if resource.group == "__global__":
                color = "blue"
                dest = cluster_global
            elif resource.group == "__base__":
                requested_feat = False
                if f"feature.{resource.name}" in self.feature_names:
                    requested_feat = True

                color = "red" if requested_feat else "purple"
                shape = "cds"
                dest = cluster_app
            elif resource.group == "__internal__":
                dest = graph
                color = "green"

            node = pydot.Node(
                resource_name,
                shape=shape,
                color=color,
                rank=rank,
                label=label,
                labeljust="l",
                nojustify=True,
            )
            dest.add_node(node)

        # Add edges for each dependency
        # print("DEP TREE")
        # pprint(dep_tree)
        # # assert False, "WIP"
        for resource_name in process_order:
            edges = dep_tree[resource_name]

            # for resource_name, edges in dep_tree.items():
            # feature_dest = resources_catalog[resource_name]

            for edge in edges:
                dependency_name = edge.provider.resource.name
                label = f"{edge.rule}"
                edge = pydot.Edge(dependency_name, resource_name, label=label)
                graph.add_edge(edge)

        # Save the graph to a file
        graph.write_png(output_file)


