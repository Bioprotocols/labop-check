import paml

from paml_check.constraints import \
    binary_temporal_constraint, \
    join_constraint, \
    unary_temporal_constaint
import pysmt
import pysmt.shortcuts

class ActivityGraph:
    class URI:
        def make_paml_uri(name):
            return f"http://bioprotocols.org/paml#{name}"

        Join = make_paml_uri("Join")
        Fork = make_paml_uri("Fork")
        Final = make_paml_uri("Final")
        Initial = make_paml_uri("Initial")
        Value = make_paml_uri("Value")
        PrimitiveExecutable = make_paml_uri("PrimitiveExecutable")

    def __init__(self, doc):
        self.doc = doc
        self.insert_func_map = {
            self.URI.Join: self._insert_join,
            self.URI.Fork: self._insert_fork,
            self.URI.Final: self._insert_final,
            self.URI.Initial: self._insert_initial,
            self.URI.Value: self._insert_value,
            self.URI.PrimitiveExecutable: self._insert_primitive_executable,
        }
        self.initial = None
        self.final = None
        self.nodes = {}
        self.execs = {}
        self.forks = {}
        self.joins = {}
        self.uri_to_node_uri_map = {}
        self.edges = []
        self._process_doc()

    def _process_doc(self):
        protocols = self.doc.find_all(lambda obj: isinstance(obj, paml.Protocol))
        for protocol in protocols:
            for activity in protocol.activities:
                self.insert_activity(activity)
            for flow in protocol.flows:
                self.insert_flow(flow)

    def _get_node_uri_for_uri(self, uri):
        if uri not in self.uri_to_node_uri_map:
            raise Exception(f"get_activity_for_node failed. No node uri found for uri: {uri}")
        return self.uri_to_node_uri_map[uri]

    def get_node_for_uri(self, uri):
        uri = self._get_node_uri_for_uri(uri)
        if uri not in self.nodes:
            raise Exception(f"get_activity_for_node failed. No node found for node uri: {uri}")
        return self.nodes[uri]

    def _insert_basic_node(self, activity):
        node_id = activity.identity
        # this holds a mapping of node uri to node object
        self.nodes[node_id] = activity
        # this holds a mappings of node associated uris to node uris
        self.uri_to_node_uri_map[node_id] = node_id

    def _insert_exec_node(self, activity):
        exec_id = activity.identity
        self.execs[exec_id] = activity

        start = self._make_exec_start(exec_id)
        self.nodes[start] = activity
        self.uri_to_node_uri_map[start] = start

        end = self._make_exec_end(exec_id)
        self.nodes[end] = activity
        self.uri_to_node_uri_map[end] = end

        self.edges.append((start, end))

        if not hasattr(activity, 'input'):
            raise Exception(f"_insert_primitive_executable failed. No input pins found on: {exec_id}")
        if not hasattr(activity, 'output'):
            raise Exception(f"_insert_primitive_executable failed. No output pins found on: {exec_id}")
        for input in activity.input:
            self.uri_to_node_uri_map[input.identity] = start
        for output in activity.output:
            self.uri_to_node_uri_map[output.identity] = end

    def _make_exec_start(self, exec_id):
        return f"{exec_id}#start"

    def _make_exec_end(self, exec_id):
        return f"{exec_id}#end"

    def insert_activity(self, activity):
        type_uri = activity.type_uri
        if type_uri not in self.insert_func_map:
            raise Exception(f"insert_activity failed due to unknown activity type: {type_uri}")
        return self.insert_func_map[type_uri](activity)

    def _insert_join(self, activity):
        self._insert_basic_node(activity)
        self.joins[activity.identity] = activity

    def _insert_fork(self, activity):
        self._insert_basic_node(activity)
        self.forks[activity.identity] = activity

    def _insert_final(self, activity):
        self._insert_basic_node(activity)
        # Final is a specialized join
        self.joins[activity.identity] = activity
        # FIXME is this a true limitation?
        if self.final is not None:
            raise Exception("Cannot support multiple Final nodes in graph")
        self.final = activity

    def _insert_initial(self, activity):
        self._insert_basic_node(activity)
        # Initial is a specialized fork
        self.forks[activity.identity] = activity
        # FIXME is this a true limitation?
        if self.initial is not None:
            raise Exception("Cannot support multiple Initial nodes in graph")
        self.initial = activity

    def _insert_value(self, activity):
        self._insert_basic_node(activity)

    def _insert_primitive_executable(self, activity):
        self._insert_exec_node(activity)

    def insert_flow(self, flow):
        source_id = str(flow.source)
        sink_id = str(flow.sink)
        # sources should pull from the end stage of an activity
        if source_id in self.execs:
            source_id = self._make_exec_end(source_id)
        # sinks should pull from the start stage of an activity
        if sink_id in self.execs:
            sink_id = self._make_exec_start(sink_id)
        source = self._get_node_uri_for_uri(source_id)
        sink = self._get_node_uri_for_uri(sink_id)
        self.edges.append((source, sink))

    def find_fork_groups(self):
        fork_groups = {f: [] for f in self.forks}
        for pair in self.edges:
            source = pair[0]
            if source in fork_groups:
                fork_groups[source].append(pair[1])
        return fork_groups

    def find_join_groups(self):
        join_groups = {j: [] for j in self.joins}
        for pair in self.edges:
            sink = pair[1]
            if sink in join_groups:
                join_groups[sink].append(pair[0])
        return join_groups

    def print_debug(self):
        print("URI to node map")
        for uri in self.uri_to_node_uri_map:
            print(f"  {uri} : {self.uri_to_node_uri_map[uri]}")
        print("----------------")

        print("Executable activities")
        for exec in self.execs:
            print(f"  {exec}")
        print("----------------")

        print("Nodes")
        for node in self.nodes:
            print(f"  {node}")
        print("----------------")

        print("Joins")
        join_groups = self.find_join_groups()
        for j in join_groups:
            print(f"  {j}")
            for join in join_groups[j]:
                print(f"    - {join}")
        print("----------------")

        print("Forks")
        fork_groups = self.find_fork_groups()
        for f in fork_groups:
            print(f"  {f}")
            for fork in fork_groups[f]:
                print(f"    - {fork}")
        print("----------------")

        print("Edges")
        for pair in self.edges:
            print(f"  {pair[0]} ---> {pair[1]}")
        print("----------------")

    # TODO this is a partially implemented pass at constraint generation. It needs a bit of work still
    # but it should at least provide some hints as to where to final relevant information in this class
    def generate_constraints(self):
        # treat each node identity (uri) as a timepoint
        timepoints = list(self.nodes.keys())
        t_inf = 10000.0
        t_epsilon = 0.0001

        timepoint_vars = {t: pysmt.shortcuts.Symbol(t, pysmt.shortcuts.REAL)
                          for t in timepoints}

        timepoint_var_domains = [pysmt.shortcuts.And(pysmt.shortcuts.GE(t, pysmt.shortcuts.Real(0.0)),
                                                     pysmt.shortcuts.LE(t, pysmt.shortcuts.Real(t_inf)))
                                 for _, t in timepoint_vars.items()]

        # HACK put something here as a placeholder until I know where/how to source this info
        def hack_time(t1, t2):
            return [[0,t_inf]]

        # FIXME I am not certain where this information was expected to be sourced from
        def determine_time_constraint(source_uri, sink_uri):
            t1 = timepoint_vars[source_uri]
            t2 = timepoint_vars[sink_uri]
            # TODO determine dd
            dd = hack_time(t1, t2)
            return binary_temporal_constraint(t1, dd, t2)
        time_constraints = [determine_time_constraint(edge[0], edge[1])
                            for edge in self.edges]

        join_constraints = []                     
        join_groups = self.find_join_groups()
        for j in join_groups:
            join_constraints.append(
                join_constraint(
                    timepoint_vars[j],
                    [timepoint_vars[uri] for uri in join_groups[j]]
                )
            )

        # fork_constraints = []                     
        # fork_groups = self.find_fork_groups()
        # for j in fork_groups:
        #     fork_constraints.append(
        #         fork_constraint(
        #             timepoint_vars[j],
        #             [timepoint_vars[uri] for uri in fork_groups[j]]
        #         )
        #     )

        # HACK put something here as a placeholder until I know where/how to source this info
        def hack_duration(start, end):
            t_P1_s = "https://bbn.com/scratch/iGEM_LUDOX_OD_calibration_2018/PrimitiveExecutable1#start"
            t_P2_s = "https://bbn.com/scratch/iGEM_LUDOX_OD_calibration_2018/PrimitiveExecutable2#start"
            t_P3_s = "https://bbn.com/scratch/iGEM_LUDOX_OD_calibration_2018/PrimitiveExecutable3#start"
            if start == t_P1_s:
                return [[3,3]]
            if start == t_P2_s:
                return [[3,3]]
            if start == t_P3_s:
                return [[10,10]]
            return [[0,100]]


        def determine_duration_constraint(exec_id):
            start = self._make_exec_start(exec_id)
            end = self._make_exec_end(exec_id)
            t1 = timepoint_vars[start]
            t2 = timepoint_vars[end]
            # TODO determine dd
            dd = hack_duration(start, end)
            return binary_temporal_constraint(t1, dd, t2)
        durations = [determine_duration_constraint(exec_id)
                     for exec_id in self.execs]

        # TODO
        events = []

        given_constraints = pysmt.shortcuts.And(timepoint_var_domains + time_constraints + join_constraints)
        hand_coded_constraints = pysmt.shortcuts.And(durations + events)
        formula = pysmt.shortcuts.And(
            given_constraints,
            hand_coded_constraints,
        #    happening_timepoint_mappings
        )
        return formula
