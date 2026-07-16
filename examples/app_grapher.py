from datetime import datetime
import os

import pydot

# Graph generation
###################################


class PaasifyGrapher:
    "Draw resource dependency graphs with shared styling"

    console_font = "Courier"

    def __init__(
        self,
        app_name,
        feature_names=None,
        show_provides=False,
        show_vars=False,
        hidden_nodes=None,
    ):
        self.app_name = app_name
        self.feature_names = feature_names or []
        self.show_provides = show_provides
        self.show_vars = show_vars
        self.hidden_nodes = set(hidden_nodes or ()) | {"__root__", "__builder__"}

        self.group_styles = [
            {
                "color": "black",
                "fillcolor": "lightgreen",
                "shape": "box",
                "legend": "App resource",
                "key": "app",
            },
            {
                "color": "blue",
                "fillcolor": "lightblue",
                "shape": "box",
                "legend": "Global resource",
                "key": "global",
            },
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
        self.styles_by_key = {s["key"]: s for s in self.group_styles}

        # Unset mod (None) means "one" at resolve time (DepBuilder default_mode="one").
        one_style = {
            "color": "#555555",
            "penwidth": "2.5",
            "legend": "one (! or default) — exactly one",
        }
        self.edge_styles = {
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
        self.edge_legend = [
            one_style,
            self.edge_styles["?"],
            self.edge_styles["+"],
            self.edge_styles["*"],
        ]

        self.graph = self._create_graph()
        self._add_legend()

    def _create_graph(self):
        return pydot.Dot(
            "my_graph",
            layout="dot",
            rankdir="LR",
            graph_type="digraph",
            newrank=True,
            bgcolor="white",
            label=f"{self.app_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            labelloc="t",
            fontname=self.console_font,
            ranksep="1.8",
            nodesep="0.6",
        )

    def style_for_resource(self, resource):
        if resource.group == "__global__":
            return self.styles_by_key["global"]
        if resource.group == "__base__":
            if f"feature.{resource.name}" in self.feature_names:
                return self.styles_by_key["base_requested"]
            return self.styles_by_key["base"]
        if resource.group == "__internal__":
            return self.styles_by_key["internal"]
        return self.styles_by_key["app"]

    def _add_legend(self):
        legend_rows = [
            '<TR><TD COLSPAN="2" ALIGN="CENTER"><B>Legend</B></TD></TR>',
            '<TR><TD COLSPAN="2" ALIGN="LEFT">Arrow: requires → provides</TD></TR>',
            '<TR><TD COLSPAN="2" ALIGN="CENTER"><B>Resources</B></TD></TR>',
        ]
        for style in self.group_styles:
            legend_rows.append(
                f'<TR><TD COLSPAN="2" BGCOLOR="{style["fillcolor"]}" BORDER="1">'
                f'{style["legend"]}</TD></TR>'
            )
        legend_rows.append(
            '<TR><TD COLSPAN="2" ALIGN="CENTER"><B>Link modifiers</B></TD></TR>'
        )
        for style in self.edge_legend:
            legend_rows.append(
                f'<TR><TD BGCOLOR="{style["color"]}" WIDTH="20"> </TD>'
                f'<TD ALIGN="LEFT">{style["legend"]}</TD></TR>'
            )
        legend_html = (
            '<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            + "".join(legend_rows)
            + "</TABLE>>"
        )
        self.graph.add_node(
            pydot.Node(
                "legend",
                shape="plaintext",
                label=legend_html,
                fontname=self.console_font,
            )
        )

    def _node_label(self, resource_name, resource):
        var_list = [f"{k}: {v}" for k, v in resource.vars.items()]
        rows = [f'<TR><TD ALIGN="LEFT"><B>{resource_name}</B></TD></TR>']
        if self.show_provides and resource.provides:
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
        if self.show_vars and var_list:
            rows.append(
                '<TR><TD ALIGN="LEFT">'
                '<FONT POINT-SIZE="9" COLOR="#666666"><I>vars:</I></FONT>'
                "</TD></TR>"
            )
            for var_line in var_list:
                rows.append(
                    f'<TR><TD ALIGN="LEFT">'
                    f'<FONT POINT-SIZE="9" COLOR="#666666">{var_line}</FONT>'
                    f"</TD></TR>"
                )
        return (
            '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" '
            'CELLPADDING="1" ALIGN="LEFT">'
            + "".join(rows)
            + "</TABLE>>"
        )

    def add_resource_node(self, resource_name, resource):
        if resource_name in self.hidden_nodes:
            return
        style = self.style_for_resource(resource)
        self.graph.add_node(
            pydot.Node(
                resource_name,
                shape=style["shape"],
                color=style["color"],
                style="filled",
                fillcolor=style["fillcolor"],
                label=self._node_label(resource_name, resource),
                fontname=self.console_font,
                labeljust="l",
                labelloc="c",
                nojustify=True,
                margin="0.15,0.1",
            )
        )

    def add_resources(self, resources):
        "Add nodes from a name→resource mapping (or ResourceManager.catalog)"
        for resource_name, resource in resources.items():
            self.add_resource_node(resource_name, resource)

    def add_require_edge(self, requirer_name, provider_name, requirement):
        "Arrow: requirer → provider (points to what is required)"
        if (
            requirer_name in self.hidden_nodes
            or provider_name in self.hidden_nodes
            or requirer_name == provider_name
        ):
            return
        edge_style = self.edge_styles.get(requirement.mod, self.edge_styles[None])
        edge_kwargs = {
            "label": requirement.rule,
            "fontcolor": "lightgrey",
            "fontname": self.console_font,
            "color": edge_style["color"],
        }
        if edge_style.get("style"):
            edge_kwargs["style"] = edge_style["style"]
        if edge_style.get("penwidth"):
            edge_kwargs["penwidth"] = edge_style["penwidth"]
        self.graph.add_edge(
            pydot.Edge(requirer_name, provider_name, **edge_kwargs)
        )

    def add_kind_match_edges(self, resources):
        "Edges for all declared requires/provides (kind match only, no remap)"
        provider_links = [
            provide
            for resource in resources.values()
            for provide in resource.provides
            if resource.name not in self.hidden_nodes
        ]
        for resource_name, resource in resources.items():
            if resource_name in self.hidden_nodes:
                continue
            for requirement in resource.requires:
                for provider in provider_links:
                    kind_match = provider.kind == requirement.kind or (
                        provider.parent is not None
                        and provider.parent.name == requirement.kind
                    )
                    if not kind_match:
                        continue
                    self.add_require_edge(
                        resource_name, provider.resource.name, requirement
                    )

    def add_dep_tree_edges(self, dep_tree, process_order):
        "Edges from a resolved dependency tree"
        for resource_name in process_order:
            if resource_name in self.hidden_nodes:
                continue
            for edge_link in dep_tree.get(resource_name, []):
                self.add_require_edge(
                    resource_name,
                    edge_link.provider.resource.name,
                    edge_link.requirement,
                )

    def write_png(self, output_file="output.png"):
        "Write PNG under artifacts/ in the current working directory"
        artifacts_dir = "artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)
        output_file = os.path.join(artifacts_dir, os.path.basename(output_file))
        self.graph.write_png(output_file)
        return output_file
