


# from paasify_v4.common import from_yaml, read_file  # , to_yaml
from helpers import from_yaml, read_file  # , to_yaml

from model import Catalog, GlobalCfg
from app import AppResolver

#################


class ResourceResolver:
    "GlobalCfg Resolver"

    def __init__(self, catalog, context):

        self.catalog = Catalog(value=catalog)
        self.context = GlobalCfg(value=context)

    def get_app_resolver(
        self,
        app_name,
        feature_names=None,
        sources=("catalog", "context"),
        resolve_features=True,
    ):
        "Return an AppResolver for the given app"

        sources = tuple(sources)
        ctx_config = self.context.features.get_value() if "context" in sources else {}
        ctx_plugins = self.context.plugins.get_value() if "context" in sources else {}
        app_config = self.catalog(app_name)

        remap_rules = self.context.remap_rules if "context" in sources else None

        app_resolver = AppResolver(
            app_name,
            app_config,
            feature_names=feature_names,
            remap_rules=remap_rules,
        )

        app_resolver.resolve(
            extra_resources=ctx_config,
            extra_plugins=ctx_plugins,
            sources=sources,
            resolve_features=resolve_features,
        )

        return app_resolver

    # def get_resources_graph(self, resources):

    # def dump_catalog(self):
    #     "Dump app catalog"

    #     for app in self.catalog:
    #         self.dump_app(app)



#################

import os

WORK_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)))


CONTEXT = from_yaml(read_file(os.path.join(WORK_DIR, "context.yml"))).get("global")
CATALOG = from_yaml(read_file(os.path.join(WORK_DIR, "catalog.yml"))).get("catalog")
OUT_PNG = os.path.join(WORK_DIR, "output.png")

def test3():

    # Base TEST1
    resolver = ResourceResolver(catalog=CATALOG, context=CONTEXT)

    USER_APP = "traefik"
    USER_FEATURES = ["expose_https", "expose_http_admin", "expose_http", "api"]
    USER_FEATURES = ["profile_http"]
    USER_FEATURES = ["expose_http2"]
    USER_FEATURES = []


    app_resolver = resolver.get_app_resolver(
        USER_APP,
        feature_names=USER_FEATURES,
    )
    print("RESOLVER app_resolver.dump_app()")
    app_resolver.dump_app()


    print("DEBUUUGGG: app_resolver.builder.dump() - ", app_resolver.builder)
    app_resolver.builder.dump()

    # Generate graph
    app_resolver.gen_graph(output_file=OUT_PNG)
    print("Graph generated in:", OUT_PNG)


# test3()




def test4():

    # Base TEST1
    resolver = ResourceResolver(catalog=CATALOG, context=CONTEXT)

    USER_APP = "traefik"
    USER_FEATURES = ["expose_https", "expose_http_admin", "expose_http", "api"]
    USER_FEATURES = ["profile_http"]
    USER_FEATURES = ["expose_http2"]
    USER_FEATURES = []


    app_resolver = resolver.get_app_resolver(
        USER_APP,
        feature_names=USER_FEATURES,
    )
    # print("RESOLVER app_resolver.dump_app()")
    # app_resolver.dump_app()


    # print("DEBUUUGGG: app_resolver.builder.dump() - ", app_resolver.builder)
    # app_resolver.builder.dump()

    # Generate graph
    OUT_PNG = os.path.join(WORK_DIR, "output_all_resources.png")
    app_resolver.gen_all_resources_graph(output_file=OUT_PNG)
    print("Graph generated in:", OUT_PNG)


# test4()


def test5():
    "Generate all-resources graphs for selected sources (catalog / context / both)"

    USER_APP = "traefik"
    USER_FEATURES = []
    SHOW_PROVIDES = True  # set False to hide provides list inside nodes
    SHOW_VARS = True  # set True to show resource vars inside nodes

    # Active source sets to generate. Add more later (e.g. "plugins").
    # Each entry is a tuple of source names.
    SOURCE_SETS = [
        ("catalog",),
        ("context",),
        ("catalog", "context"),
    ]
    # Or run a single set:
    # SOURCE_SETS = [("catalog", "context")]

    resolver = ResourceResolver(catalog=CATALOG, context=CONTEXT)

    for sources in SOURCE_SETS:
        app_resolver = resolver.get_app_resolver(
            USER_APP,
            feature_names=USER_FEATURES,
            sources=sources,
            resolve_features=False,
        )
        tag = "_".join(sources)
        out_png = os.path.join(WORK_DIR, f"output_all_resources_{tag}.png")
        app_resolver.gen_all_resources_graph(
            output_file=out_png,
            show_provides=SHOW_PROVIDES,
            show_vars=SHOW_VARS,
        )
        print(f"Graph [{tag}] generated in: {out_png}")


# test4()
test5()

# from pyinstrument import Profiler
# with Profiler(interval=0.1) as profiler:
#     test3()

# profiler.print()
