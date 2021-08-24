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
        self.activty_pretty_strings = self._get_activity_pretty_strings()

    def _get_activity_pretty_strings(self):
        activity_pretty_strings = { a: a for a in self.activities }
        for _, protocol in self.activity_graph.protocols.items():
            for node in protocol.ref.nodes:
                if node.identity in self.activities:
                    if isinstance(node, uml.CallBehaviorAction):
                        activity_pretty_strings[node.identity] = f"{node.behavior}\n{node.identity}"
                    elif isinstance(node, uml.InitialNode) or \
                         isinstance(node, uml.ForkNode) or \
                         isinstance(node, uml.JoinNode) or \
                         isinstance(node, uml.FlowFinalNode):
                        activity_pretty_strings[node.identity] = f"{node.display_id}\n{node.identity}"
                    else :
                        activity_pretty_strings[node.identity] = f"{node.identity}"
        return activity_pretty_strings

    def _is_start_timepoint(self, tp):
        return literal_eval("%s" % str(tp)).startswith("start")

    def _is_end_timepoint(self, tp):
        return literal_eval("%s" % str(tp)).startswith("end")

    def _get_activity(self, tp):
        return literal_eval("%s" % str(tp)).split(":", 1)[1]

    def _to_date_time(self, val):
        f_val = float(val.constant_value())
        return self.start_time + timedelta(seconds=f_val)

    def to_df(self):
        df = pd.DataFrame([
            dict(Task=self.activty_pretty_strings[activity], Start=self.start_times[activity], Finish=self.end_times[activity])
            for activity in self.activities
        ])
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