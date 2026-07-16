from pprint import pprint

from superconf.configuration import (
    ConfigurationObj,
    ConfigurationDict,
    ConfigurationList,
    NOT_SET,
)
from superconf.fields import (
    Field,
    FieldConf,
    FieldDict,
    FieldList,
    FieldBool,
    FieldString,
)

from resource_manager.links import (
    ResourceLink,
)


###################################
# Generic Base components
###################################


# Feature links
###################################


class FeatureLink(ConfigurationObj):
    """Feature link"""

    kind = FieldString(help="Kind")
    instance = Field(help="Instance name")
    # mod = FieldString(help="Modifier", default="one")
    mod = Field(help="Modifier", default=None)
    raw_value = Field(help="Raw value (Internal)")

    def pre_load(self, value):
        "Allow string config for requirement rule on pre_load hook"

        if value is NOT_SET:
            value = {}

        return ResourceLink.parse_config(None, value)


class FeatureLinks(ConfigurationList):
    "List of feature links"

    class Meta:
        children_class = FeatureLink
        default = []


class FeatureResource(ConfigurationObj):
    """FeatureResource"""

    class Meta:
        extra_fields = False

    # name = FieldString(help="FeatureResource name")
    provides = FieldConf(FeatureLinks, help="Provides")
    requires = FieldConf(FeatureLinks, help="Requires")


# Plugin links
###################################


class PluginLink(FeatureLink):
    """Plugin link"""

    mod = FieldString(help="Modifier", default="one_or_many")

    # def post_load(self):
    #     "Post load hook"
    #     print(">>>>>>>>>> POST LOAD PLUGIN LINK", self)


class PluginList(ConfigurationList):
    "List of plugin links"

    class Meta:
        children_class = PluginLink
        default = []


class PluginResource(FeatureResource):
    """Plugin resource"""

    class Meta:
        extra_fields = False

    # name = FieldString(help="FeatureResource name")
    provides = FieldConf(PluginList, help="Provides")
    requires = FieldConf(PluginList, help="Requires")


###################################
# Paasify Base components
###################################


class PaasifyFeature(FeatureResource):
    """Paasify Feature"""

    class Meta:
        extra_fields = False

    desc = FieldString(help="Description")

    group = FieldString(help="Default group", default="__global__")
    group_mode = FieldString(help="Group modifier", default="zero_or_many")
    group_default = FieldString(help="Default group instance", default="default")

    # provides = FieldList(help="Provides")
    # requires = FieldList(help="Requires")
    # provides = FieldConf(ConfigurationList, children_class=ProvideLink)
    # requires = FieldConf(ConfigurationList, children_class=RequireLink)

    # internal = FieldBool(default=False, help="Internal resource")
    auto_enable = FieldBool(default=True, help="Auto enable")
    vars = FieldDict(help="Vars")


class PaasifyPlugin(PluginResource):
    """Paasify Plugin"""

    class Meta:
        extra_fields = False

    # class Meta:
    #     extra_fields = True
    desc = FieldString(help="Description")

    public = FieldBool(default=True, help="Public plugin if true")
    availability = FieldString(help="Default availability", default="on_start")
    kind = FieldString(help="Plugin kind", default="plugin")

    def post_load(self):
        "Post load hook"
        # Auto append as feature
        # if self.group == "__base__":
        feature_name = f"plugin.{self.__node_key__}"
        if not feature_name in self.provides:
            print("POST LOAD PLUGIN, INSET FEATURE FOR", feature_name)
            new_val = list(self.provides.get_value())
            new_val.insert(0, feature_name)
            self.provides.set_value(new_val)


class PaasifyFeatures(ConfigurationDict):
    """Paasify Features"""

    class Meta:
        children_class = PaasifyFeature


class PaasifyPlugins(ConfigurationDict):
    """Paasify Plugins"""

    class Meta:
        children_class = PaasifyPlugin


###################################
# Paasify App components
###################################


class PaasifyAppFeature(PaasifyFeature):

    """Main PaasifyFeature"""

    class Meta:
        extra_fields = False

    group = FieldString(help="Default group", default="__base__")

    # provides = FieldConf(FeatureProvidesList, help="Provides")
    # requires = FieldConf(FeatureLinks, help="Requires")
    # provides = FieldConf(ConfigurationList, children_class=ProvideLink)
    # requires = FieldConf(ConfigurationList, children_class=RequireLink)

    def post_load(self):
        "Post load hook"
        # Auto append as feature
        if self.group == "__base__":
            feature_name = f"feature.{self.__node_key__}"
            if not feature_name in self.provides:
                # print("POST LOAD FEATURE, INSET FEATURE FOR", feature_name)

                new_val = list(self.provides.get_value())
                new_val.insert(0, feature_name)
                self.provides.set_value(new_val)


class PaasifyAppFeatures(ConfigurationDict):
    """App Features PaasifyFeature"""

    class Meta:
        children_class = PaasifyAppFeature


###################################
# Paasify Top components
###################################


class GlobalCfg(ConfigurationObj):
    """Global configuration"""

    class Meta:
        extra_fields = False

    # Application configuration
    resource_model = FieldDict(help="resource model")
    remap_rules = FieldDict(help="WIP")

    # plugins = FieldDict()
    features = FieldConf(PaasifyFeatures)
    plugins = FieldConf(PaasifyPlugins)


class App(ConfigurationObj):
    """Main App"""

    class Meta:
        extra_fields = False

    # Application configuration
    default_features = FieldList(help="default features")
    resource_model = FieldDict(help="resource model")

    # plugins = FieldDict(help="WIP")
    remap_rules = FieldDict(help="WIP")

    # plugins = FieldDict()
    plugins = FieldConf(PaasifyPlugins)

    # TEST WIPPPPP
    features = FieldConf(PaasifyAppFeatures)  ## OKKK
    # features = FieldConf(instance_class=ConfigurationDict, children_class=PaasifyAppFeature)    


    # features = FieldConf(PaasifyFeatures)

    # features = FieldConf(ConfigurationDict, children_class=PaasifyAppFeature)  # TOFIX
    # features = FieldDict(instance_class=PaasifyAppFeatures)
    # features = FieldDict(instance_class=PaasifyAppFeature)


class Catalog(ConfigurationDict):
    """Main App catalog"""

    class Meta:
        children_class = App
