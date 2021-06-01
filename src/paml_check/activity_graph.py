import math

import paml
import sbol3
import tyto

from paml_check.constraints import \
    binary_temporal_constraint, \
    join_constraint, \
    unary_temporal_constaint, \
    anytime_before, \
    determine_time_constraint, \
    duration_constraint
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

    def __init__(self, doc, epsilon=0.0001, infinity=10e10):
        self.doc = doc
        self.epsilon = epsilon
        self.infinity = infinity
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
        self.protocols = {}
        self.edges = []
        self._process_doc()

        ## Variables used to link solutions back to the doc
        self.var_to_node = {} # SMT variable to graph node map

    def _process_doc(self):
        protocols = self.doc.find_all(lambda obj: isinstance(obj, paml.Protocol))
        for protocol in protocols:
            self.protocols[protocol.identity] = protocol
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

        start_time = activity.start.value if hasattr(activity, "start") else None
        end_time = activity.end.value if hasattr(activity, "end") else None
        duration = activity.duration.value if hasattr(activity, "duration") else None

        difference = [[self.epsilon, math.inf]]
        if duration:
            difference.append([duration.value, duration.value])
        if start_time and end_time:
            d = end_time.value - start_time.value
            difference.append([d, d])
        intersected_difference = ActivityGraph._intersect(difference)

        self.edges.append((start, [intersected_difference], end))

        if not hasattr(activity, 'input'):
            raise Exception(f"_insert_primitive_executable failed. No input pins found on: {exec_id}")
        if not hasattr(activity, 'output'):
            raise Exception(f"_insert_primitive_executable failed. No output pins found on: {exec_id}")
        for input in activity.input:
            self.uri_to_node_uri_map[input.identity] = start
        for output in activity.output:
            self.uri_to_node_uri_map[output.identity] = end

    def _intersect(difference):
        """
        Compute the intersection of intervals appearing in the difference list
        :return: interval
        """
        interval = None
        for d in difference:
            if not interval:
                interval = d
            else:
                interval[0] = d[0] if interval[0] <= d[0] and d[0] <= interval[1] else interval[0]
                interval[1] = d[1] if interval[0] <= d[1] and d[1] <= interval[1] else interval[1]
        return interval

    def _make_exec_start(self, exec_id):
        return f"{exec_id}#start"

    def _make_exec_end(self, exec_id):
        return f"{exec_id}#end"

    def _make_exec_duration(self, exec_id):
        return f"{exec_id}#duration"

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

        ## This constraint assumes that it connects a source's end time to a sink's start time
        source_node = self.nodes[source]
        sink_node = self.nodes[sink]
        source_time = source_node.end.value if hasattr(source_node, "end") and hasattr(source_node.end, "value") else None
        sink_time = sink_node.start.value if hasattr(sink_node, "start") and hasattr(sink_node.start, "value") else None

        difference = [[0.0, math.inf]]
        if source_time and sink_time:
            d = end_time.value - start_time.value
            difference.append([d, d])
        intersected_difference = ActivityGraph._intersect(difference)

        self.edges.append((source, [intersected_difference], sink))

    def find_fork_groups(self):
        fork_groups = {f: [] for f in self.forks}
        for pair in self.edges:
            source = pair[0]
            if source in fork_groups:
                fork_groups[source].append(pair[1])
        return fork_groups

    def find_join_groups(self):
        join_groups = {j: [] for j in self.joins}
        for (source, _, sink) in self.edges:
            if sink in join_groups:
                join_groups[sink].append(source)
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

    def _substitute_infinity(self, interval_list):
        for interval in interval_list:
            interval[0] = self.infinity if interval[0] == math.inf else interval[0]
            interval[1] = self.infinity if interval[1] == math.inf else interval[1]
        return interval_list

    # TODO this is a partially implemented pass at constraint generation. It needs a bit of work still
    # but it should at least provide some hints as to where to final relevant information in this class
    def generate_constraints(self):
        # treat each node identity (uri) as a timepoint
        timepoints = list(self.nodes.keys())
        duration_vars = {a : pysmt.shortcuts.Symbol(self._make_exec_duration(a),
                                                    pysmt.shortcuts.REAL)
                         for a in list(self.execs.keys())}

        timepoint_vars = {t: pysmt.shortcuts.Symbol(t, pysmt.shortcuts.REAL)
                          for t in timepoints}

        self.var_to_node = { v: k for k, v in timepoint_vars.items() }

        protocol_constraints = self._make_protocol_constraints(timepoint_vars)

        timepoint_var_domains = [pysmt.shortcuts.And(pysmt.shortcuts.GE(t, pysmt.shortcuts.Real(0.0)),
                                                     pysmt.shortcuts.LE(t, pysmt.shortcuts.Real(self.infinity)))
                                 for _, t in timepoint_vars.items()]

        time_constraints = [binary_temporal_constraint(timepoint_vars[source],
                                                       self._substitute_infinity(disjunctive_distance),
                                                       timepoint_vars[sink])
                            for (source, disjunctive_distance, sink) in self.edges]

        duration_constraints = [
            duration_constraint(timepoint_vars[self._make_exec_start(a)],
                                timepoint_vars[self._make_exec_end(a)],
                                v)
            for a, v in duration_vars.items()
        ]

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

        # TODO
        events = []

        given_constraints = pysmt.shortcuts.And(timepoint_var_domains + \
                                                time_constraints + \
                                                join_constraints + \
                                                protocol_constraints
                                                #duration_constraints
                                                )

        return given_constraints

    def _make_protocol_constraints(self, timepoint_vars):
        """
        Add constraints that:
         - link initial to protocol start
         - link final to protocol end
         - link duration to end - start
        :return:
        """
        protocol_start_constraints = []
        protocol_end_constraints = []
        protocol_duration_constraints = []

        for protocol_id, protocol in self.protocols.items():
            protocol_start_id = self._make_exec_start(protocol_id)
            protocol_end_id = self._make_exec_end(protocol_id)
            protocol_duration_id = self._make_exec_duration(protocol_id)

            protocol_start_var = pysmt.shortcuts.Symbol(protocol_start_id,
                                                        pysmt.shortcuts.REAL)
            protocol_end_var = pysmt.shortcuts.Symbol(protocol_end_id,
                                                      pysmt.shortcuts.REAL)
            protocol_duration_var = pysmt.shortcuts.Symbol(protocol_duration_id,
                                                           pysmt.shortcuts.REAL)

            self.var_to_node[protocol_start_var] = protocol_start_id
            self.var_to_node[protocol_end_var] = protocol_end_id
            self.var_to_node[protocol_duration_var] = protocol_duration_id

            protocol_duration_constraints.append(
                duration_constraint(protocol_start_var,
                                    protocol_end_var,
                                    protocol_duration_var))


            initial_node = protocol.initial()
            start_constraint = pysmt.shortcuts.Equals(protocol_start_var,
                                                      timepoint_vars[initial_node.identity])
            protocol_start_constraints.append(start_constraint)

            final_node = protocol.final()
            end_constraint = pysmt.shortcuts.Equals(protocol_end_var,
                                                      timepoint_vars[final_node.identity])
            protocol_end_constraints.append(end_constraint)

        return  protocol_start_constraints + protocol_end_constraints # + protocol_duration_constraints


    def add_result(self, doc, result):
        if result:
            for var, value in result:
                v = float(value.constant_value())
                graph_node = self.var_to_node[var]
                is_start = graph_node.endswith("#start")
                is_end = graph_node.endswith("#end")
                is_duration = graph_node.endswith("#duration")

                doc_node = self.nodes[graph_node]
                if is_start:
                    doc_node.start.value = sbol3.Measure(v, tyto.OM.time)
                elif is_end:
                    doc_node.end.value = sbol3.Measure(v, tyto.OM.time)
                elif is_duration:
                    doc_node.duration.value = sbol3.Measure(v, tyto.OM.time)
                else:
                    doc_node.start.value = sbol3.Measure(v, tyto.OM.time)
                    doc_node.end.value = sbol3.Measure(v, tyto.OM.time)
                    doc_node.duration.value = sbol3.Measure(0.0, tyto.OM.time)

        return doc

