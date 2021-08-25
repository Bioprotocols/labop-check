import datetime
from ast import literal_eval
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
import uml

class Schedule(object):

    def __init__(self, model, graph, start_time=datetime.datetime.utcnow()):
        self.start_time = start_time
        self.start_times = {self._get_activity(tp) : self._to_date_time(val) for (tp, val) in model if self._is_start_timepoint(tp) }
        self.end_times = {self._get_activity(tp): self._to_date_time(val) for (tp, val) in model if self._is_end_timepoint(tp)}
        self.activities = self.start_times.keys()
        self.activity_graph = graph
        self.activity_pretty_strings = self._get_activity_pretty_strings()

    def _make_pretty_node_identity(self, node, protocol):
        return node.identity.replace(f"{protocol.identity}/", "")

    def _make_pretty_node_behavior(self, node):
        return node.behavior.rsplit("/", 1)[1]

    def _get_activity_pretty_strings(self):
        activity_pretty_strings = {}
        idx = 0
        for _, protocol in self.activity_graph.protocols.items():
            idx += 1
            superscript = f"<sup>{idx}</sup>"
            activity_pretty_strings[protocol.identity] = f"<b>{protocol.identity}</b>{superscript}"
            for node in protocol.ref.nodes:
                pid = f"{self._make_pretty_node_identity(node, protocol)}"
                if node.identity in self.activities:
                    if isinstance(node, uml.CallBehaviorAction):
                        activity_pretty_strings[node.identity] = f"<i>{self._make_pretty_node_behavior(node)}</i> {pid}{superscript}"
                    elif isinstance(node, uml.InitialNode) or \
                         isinstance(node, uml.ForkNode) or \
                         isinstance(node, uml.JoinNode) or \
                         isinstance(node, uml.FlowFinalNode):
                        activity_pretty_strings[node.identity] = f"{pid}{superscript}"
                    else :
                        activity_pretty_strings[node.identity] = f"{pid}{superscript}"
        return activity_pretty_strings

    def _is_start_timepoint(self, tp):
        return literal_eval("%s" % str(tp)).startswith("start")

    def _is_end_timepoint(self, tp):
        return literal_eval("%s" % str(tp)).startswith("end")

    def _get_activity(self, tp):
        return literal_eval("%s" % str(tp)).split("_", 1)[1]

    def _to_date_time(self, val):
        f_val = float(val.constant_value())
        return self.start_time + timedelta(seconds=f_val)

    def to_df(self):
        df = pd.DataFrame([
            dict(Task=self.activity_pretty_strings[activity], Start=self.start_times[activity], Finish=self.end_times[activity])
            for activity in self.activities
        ])
        df = df.sort_values(by="Start")
        return df

    def plot(self, filename=None, show=False):
        df = self.to_df()
        #df.to_csv("plot_data.csv")
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task")
        fig.update_yaxes(autorange="reversed")  # otherwise tasks are listed from the bottom up
        if filename:
            with open(filename, "wb") as f:
                f.write(fig.to_image("pdf", scale=4))
        if show:
            fig.show()

        return fig