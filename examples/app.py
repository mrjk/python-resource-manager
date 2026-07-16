import sys
from pprint import pprint

# import networkx as nx
# from collections import defaultdict
# from types import SimpleNamespace

import logging

# from graphlib import TopologicalSorter


# from examples.model import (
#     Catalog,
#     # App,
#     GlobalCfg,
#     # ContextFeature,
#     # ProvideLink,
#     # RequireLink,
# )

from app_grapher import PaasifyGrapher

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

        grapher = PaasifyGrapher(
            app_name=self.app_name,
            feature_names=self.feature_names,
            show_provides=show_provides,
            show_vars=show_vars,
            hidden_nodes={self.builder.root_node_name},
        )
        resources = self.builder.rmanager.catalog
        grapher.add_resources(resources)
        grapher.add_kind_match_edges(resources)
        return grapher.write_png(output_file)

    def gen_graph_raw(self, output_file="output.png"):
        "Generate a graph of the app dependencies"

        self.builder.gen_graph(output_file)

    def gen_graph(
        self,
        output_file="output.png",
        show_provides=False,
        show_vars=False,
    ):
        "Generate a graph of the resolved app dependencies"

        grapher = PaasifyGrapher(
            app_name=self.app_name,
            feature_names=self.feature_names,
            show_provides=show_provides,
            show_vars=show_vars,
            hidden_nodes={self.builder.root_node_name},
        )
        resources_catalog = self.builder.rmanager
        process_order = self.builder.dep_order
        for resource_name in process_order:
            grapher.add_resource_node(
                resource_name, resources_catalog.get_resource(resource_name)
            )
        grapher.add_dep_tree_edges(self.builder.dep_tree, process_order)
        return grapher.write_png(output_file)


