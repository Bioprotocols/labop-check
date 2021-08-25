from logging import warning
import math
import paml
import uml
import graphviz

from paml_check.constraints import \
    binary_temporal_constraint, \
    join_constraint, \
    unary_temporal_constaint, \
    duration_constraint
from paml_check.utils import Interval
# from paml_check.minimize_duration import MinimizeDuration
from paml_check.convert_constraints import ConstraintConverter

import paml_time as pamlt # May be unused but is required to access paml_time values

import pysmt

class TimeVariable:
    def __init__(self, prefix, ref):
        self.ref = ref
        self.prefix = prefix
        self.name = f"{prefix}:{ref.identity}"
        self.symbol = pysmt.shortcuts.Symbol(self.name, pysmt.shortcuts.REAL)
        self.value = None

    def to_dot(self):
        return self.name.replace(":", "_")

class TimeVariableGroup(dict):
    DURATION_VARIABLE = 'duration'
    START_TIME_VARIABLE = 'start'
    END_TIME_VARIABLE = 'end'

    @property
    def start(self):
        return self[self.START_TIME_VARIABLE]

    @property
    def end(self):
        return self[self.END_TIME_VARIABLE]

    @property
    def duration(self):
        return self[self.DURATION_VARIABLE]

    def _define_time_variable(self, prefix, ref):
        self[prefix] = TimeVariable(prefix, ref)

    def __init__(self, ref):
        self._define_time_variable(self.START_TIME_VARIABLE, ref)
        self._define_time_variable(self.END_TIME_VARIABLE, ref)
        self._define_time_variable(self.DURATION_VARIABLE, ref)
        self.ref = ref

    def to_dot(self):
        graph = graphviz.Digraph(name=f"cluster_{self.ref.identity}")
        src = self[self.START_TIME_VARIABLE].to_dot()
        dest = self[self.END_TIME_VARIABLE].to_dot()
        graph.node(src)
        graph.node(dest)
        #graph.edge(src, dest)
        return graph

class Protocol:
    @property
    def identity(self):
        return self.ref.identity

    @property
    def time_variables(self):
        return self.identity_to_time_variables(self.ref.identity)

    @property
    def initial_time_variables(self):
        return self.identity_to_time_variables(self.initial.identity)

    @property
    def final_time_variables(self):
        return self.identity_to_time_variables(self.final.identity)

    def __init__(self, ref: paml.Protocol, epsilon=0.0001, infinity=10e10):
        self.node_func_map = {
            uml.JoinNode: self._insert_join,
            uml.ForkNode: self._insert_fork,
            uml.FlowFinalNode: self._insert_final,
            uml.InitialNode: self._insert_initial,
            uml.CallBehaviorAction: self._insert_call_behavior_action
        }
        self.edge_func_map = {
            uml.ControlFlow: self._insert_control_flow,
            uml.ObjectFlow: self._insert_object_flow
        }

        self.ref = ref
        self.epsilon = epsilon
        self.infinity = infinity

        self.control_flow = []
        self.object_flow = []


        self.initial = self.ref.initial()
        self.final = self.ref.final()

        self.fork_groups = {}
        self.join_groups = {}

        # Build identity map
        self.identity_to_ref = {}
        self.identity_to_ref[self.initial.identity] = self.initial
        self.identity_to_ref[self.final.identity] = self.final
        for node in self.ref.nodes:
            self.identity_to_ref[node.identity] = node

        # Build time variables
        self.time_edges = []
        self.time_variable_groups = {}
        self.define_time_variable_group(self.initial)
        self.define_time_variable_group(self.final)
        for node in self.ref.nodes:
            self.define_time_variable_group(node)

        self._insert_nodes()
        self._insert_edges()

        # Run these last since they depend on the object flow
        #self.repair_nodes_with_no_in_flow()
        self.repair_nodes_with_no_out_flow() ## Needed because final node has no in flows currently

        ## Bind protocol start and end times with initial and final nodes
        self.define_time_variable_group(self.ref)
        self._insert_time_edge(self.time_variable_groups[self.ref.identity].start,
                               self.time_variable_groups[self.initial.identity].start,
                               0, max_dur=0)
        self._insert_time_edge(self.time_variable_groups[self.final.identity].end,
                               self.time_variable_groups[self.ref.identity].end,
                               0, max_dur=0)

    def _insert_nodes(self):
        for node in self.ref.nodes:
            self._insert_activity_node(node)

    def _insert_edges(self):
        for edge in self.ref.edges:
            self._insert_activity_edge(edge)

    def to_dot(self):
        def _node_name(node):
            return node.name.replace(":", "_")

        try:
            dot = graphviz.Digraph(name=self.identity)
            for edge in self.time_edges:
                src = edge[0].to_dot()
                dest = edge[2].to_dot()
                dot.node(src)
                dot.node(dest)
                dot.edge(src, dest, label=str(edge[1]))
            # Make clusters for each activity
            for name, tvg in self.time_variable_groups.items():
                if name != self.ref.identity:  # Don't group the protocol start/end nodes
                    subgraph = tvg.to_dot()
                    dot.subgraph(subgraph)
        except Exception as e:
            print(f"Cannot translate to graphviz: {e}")
        return dot

    def collect_time_symbols(self):
        variables = []
        for _, grp in self.time_variable_groups.items():
            for _, v in grp.items():
                variables.append(v.symbol)
        return variables

    def define_time_variable_group(self, ref):
        self.time_variable_groups[ref.identity] = TimeVariableGroup(ref)
    
    def identity_to_time_variables(self, identity):
        org_identity = str(identity)
        while identity not in self.time_variable_groups:
            res = identity.rsplit('/', 1)
            if len(res) == 1:
                break
            identity = res[0]
        if identity not in self.time_variable_groups:
            raise Exception(f"Failed to find node for {org_identity}")
        return self.time_variable_groups[identity]

    def identity_to_node(self, identity):
        org_identity = str(identity)
        while identity not in self.identity_to_ref:
            res = identity.rsplit('/', 1)
            if len(res) == 1:
                break
            identity = res[0]
        if identity not in self.identity_to_ref:
            raise Exception(f"Failed to find node for {org_identity}")
        return self.identity_to_ref[identity]

    def _insert_activity_node(self, node):
        tvs = self.identity_to_time_variables(node.identity)
        if isinstance(node, uml.ExecutableNode):
            self._insert_time_edge(tvs.start, tvs.end, self.epsilon)
        else:
            self._insert_time_edge(tvs.start, tvs.end, 0)
        if node != self.initial:
            self._insert_succeeds_initial_edge(tvs)
        if node != self.final:
            self._insert_precedes_final_edge(tvs)

        # Handle any type specific inserts
        t = type(node)
        if t not in self.node_func_map:
            warning(f"Skipping processing of node {node.identity}. No handler function found.")
            return
        self.node_func_map[t](node)

    def _insert_activity_edge(self, edge):
        source = self.identity_to_time_variables(str(edge.source))
        target = self.identity_to_time_variables(str(edge.target))
        if target.start in self.join_groups:
            self.join_groups[target.start].append(source.end)
        if source.end in self.fork_groups:
            self.fork_groups[source.end].append(target.start)

        # Handle any type specific inserts
        t = type(edge)
        if t not in self.edge_func_map:
            warning(f"Skipping processing of edge {edge.identity}. No handler function found.")
            return
        self.edge_func_map[t](edge)

    def _insert_succeeds_initial_edge(self, target):
        source = self.identity_to_time_variables(str(self.initial.identity))
        self._insert_time_edge(source.end, target.start, 0)

    def _insert_precedes_final_edge(self, source):
        target = self.identity_to_time_variables(str(self.final.identity))
        self._insert_time_edge(source.end, target.start, 0)

    def _insert_control_flow(self, edge):
        self.control_flow.append(edge)
        source = self.identity_to_time_variables(str(edge.source))
        target = self.identity_to_time_variables(str(edge.target))
        self._insert_time_edge(source.end, target.start, 0)

    def _insert_object_flow(self, edge):
        self.object_flow.append(edge)
        source = self.identity_to_time_variables(str(edge.source))
        target = self.identity_to_time_variables(str(edge.target))
        self._insert_time_edge(source.end, target.start, 0)

    def _insert_time_edge(self, start, end, min_d, max_dur=math.inf):
        difference = [[min_d, max_dur]]
        if start.value and end.value:
            d = end.value - start.value
            difference.append([d, d])
        intersected_difference = Interval.intersect(difference)
        new_edge = (start, [intersected_difference], end)
        if new_edge not in self.time_edges:
            self.time_edges.append(new_edge)

    def _insert_join(self, node):
        v = self.identity_to_time_variables(node.identity)
        self.join_groups[v.start] = []

    def _insert_fork(self, node):
        v = self.identity_to_time_variables(node.identity)
        self.fork_groups[v.end] = []

    def _insert_initial(self, node):
        self._insert_fork(node)

    def _insert_final(self, node):
        self._insert_join(node)

    def _insert_call_behavior_action(self, node):
        pass # We currently don't use these for anything type specific

    def _make_protocol_constraints(self):
        protocol_start = self.time_variables.start.symbol
        protocol_end = self.time_variables.end.symbol
        initial_start = self.initial_time_variables.start.symbol
        final_end = self.final_time_variables.end.symbol
        start_constraint = pysmt.shortcuts.Equals(protocol_start, initial_start)
        end_constraint = pysmt.shortcuts.Equals(protocol_end, final_end)
        return [start_constraint, end_constraint]

    def _make_join_constraints(self):
        join_constraints = []
        for j, grp in self.join_groups.items():
            join_constraints.append(
                join_constraint(
                    j.symbol,
                    [v.symbol for v in grp]
                )
            )
        return join_constraints

    def generate_constraints(self):
        symbols = self.collect_time_symbols()

        timepoint_var_domains = [pysmt.shortcuts.And(pysmt.shortcuts.GE(s, pysmt.shortcuts.Real(0.0)),
                                                     pysmt.shortcuts.LE(s, pysmt.shortcuts.Real(self.infinity)))
                                 for s in symbols]

        time_constraints = [binary_temporal_constraint(start.symbol,
                                                       Interval.substitute_infinity(self.infinity, disjunctive_distance),
                                                       end.symbol)
                            for (start, disjunctive_distance, end) in self.time_edges]
        
        join_constraints = self._make_join_constraints()

        return pysmt.shortcuts.And( \
            timepoint_var_domains + \
            time_constraints + \
            join_constraints
        )

    # TODO remove once final nodes are provided in document
    def repair_nodes_with_no_out_flow(self):
        final = self.identity_to_time_variables(self.final.identity)
        results = []
        for node in self.ref.nodes:
            found = False
            for edge in self.object_flow:
                source = self.identity_to_time_variables(str(edge.source))
                if source.end.ref == node:
                    found = True
                    break
            if found is False:
                results.append(self.identity_to_time_variables(node.identity))
        if len(results) > 0:
            warning("Repairing out flow")
            for result in results:
                if isinstance(result.end.ref, uml.InitialNode):
                    continue
                if isinstance(result.end.ref, uml.FlowFinalNode):
                    continue
                warning(f"  {result.end.ref.identity}--->{final.start.ref.identity}")
                self._insert_time_edge(result.end, final.start, 0)
                if final.start in self.join_groups:
                    self.join_groups[final.start].append(result.end)
                if result.end in self.fork_groups:
                    self.fork_groups[result.end].append(final.start)

    # TODO remove once initial nodes are provided in document
    def repair_nodes_with_no_in_flow(self):
        initial = self.identity_to_time_variables(self.initial.identity)
        results = []
        for node in self.ref.nodes:
            found = False
            for edge in self.object_flow:
                target = self.identity_to_time_variables(str(edge.target))
                if target.start.ref == node:
                    found = True
                    break
            if found is False:
                results.append(self.identity_to_time_variables(node.identity))
        if len(results) > 0:
            warning("Repairing in flow")
            for result in results:
                if isinstance(result.start.ref, uml.InitialNode):
                    continue
                if isinstance(result.start.ref, uml.FlowFinalNode):
                    continue
                warning(f"  {initial.end.ref.identity}--->{result.start.ref.identity}")
                self._insert_time_edge(initial.end, result.start, 0)
                if result.start in self.join_groups:
                    self.join_groups[result.start].append(initial.end)
                if initial.end in self.fork_groups:
                    self.fork_groups[initial.end].append(result.start)

    def link_protocols(self, protocols):
        """
        Make time edges between calling behavior and the start and end of the subprotocols.
        :param protocols:
        :return:
        """
        for node in self.ref.nodes:
            if isinstance(node, uml.CallBehaviorAction) and \
               str(node.behavior) in protocols:

                node_start = self.time_variable_groups[node.identity].start
                node_end = self.time_variable_groups[node.identity].end
                sub_protocol = protocols[str(node.behavior)]
                sub_protocol_start = sub_protocol.time_variables.start
                sub_protocol_end = sub_protocol.time_variables.end

                ## The subprotocol time span equals the calling behavior time span
                self._insert_time_edge(node_start, sub_protocol_start, 0, max_dur=0)
                self._insert_time_edge(sub_protocol_end, node_end, 0, max_dur=0)
    
    def print_debug(self):
        def dprint(msg):
            msg = msg.replace(f":{self.ref.identity}/", " | ")
            msg = msg.replace(f":{self.ref.identity}", " | Protocol")
            msg = msg.replace(f"end |", "e |")
            msg = msg.replace(f"start |", "s |")
            print(msg)
        try:
            # dprint("Control Flow")
            # for edge in self.control_flow:
            #     dprint(f"  {edge.identity}")
            # dprint("----------------")

            # dprint("Object Flow")
            # for edge in self.object_flow:
            #     dprint(f"  {edge.identity}")
            # dprint("----------------")

            dprint("  Time Edges")
            for edge in self.time_edges:
                dprint(f"    | {edge[0].name}")
                dprint(f"    v {edge[2].name}\n")
            print("  ----------------")

            dprint("  Joins")
            for j, grp in self.join_groups.items():
                dprint(f"    {j.name}")
                for v in grp:
                    dprint(f"      - {v.name}")
            print("  ----------------")

            dprint("  Forks")
            for f, grp in self.fork_groups.items():
                dprint(f"    {f.name}")
                for v in grp:
                    dprint(f"      - {v.name}")
            print("  ----------------")
        except Exception as e:
            print(f"Error during print_debug: {e}")
    

    def print_variables(self, model):
        def dprint(msg):
            msg = msg.replace(f"{self.ref.identity}/", "")
            print(msg)
        dprint("  Time Variables")
        for name, grp in self.time_variable_groups.items():
            dprint(f"    {name}")
            for _, var in grp.items():
                dprint(f"      {var.prefix} = {float(model[var.symbol].constant_value())}")
            print("")
        print("  ----------------")

class TimeConstraints(object):

    def __init__(self, ref : pamlt.TimeConstraints, activity_graph ):
        self.ref = ref
        self.activity_graph = activity_graph

    def extract_time_constraints(self):
        cc = ConstraintConverter(self)
        time_constraints = self.ref
        doc = time_constraints.document
        count = len(time_constraints.constraints)

        # no constraints were specified
        if count == 0:
            # FIXME what shortcut is approriate to return when no constraints are specified?
            return pysmt.shortcuts.TRUE()

        # exactly one constraint was specified
        if count == 1:
            return cc.convert_constraint(time_constraints.constraints)

        # more than one constraint was specified
        # so fallback to an implicit And
        warning(f"Time Constraints with identity '{time_constraints.indentity}' provided multiple top level constraints."
                + "\n  These will be treated as an implicit And operation. This is not recommended.")
        clauses = [ cc.convert_constraint(tc_ref)
                    for tc_ref in time_constraints.constraints ]
        return pysmt.shortcuts.And(clauses)

    def _get_protocol_of_identity(self, identity):
        org_identity = str(identity)

        while identity not in self.ref.protocols:
            res = identity.rsplit('/', 1)
            if len(res) == 1:
                break
            identity = res[0]
        if identity not in self.ref.protocols:
            raise Exception(f"Failed to find  node for constraint on {org_identity}")
        return identity

    def identity_to_time_variables(self, identity):
        return self.activity_graph.protocols[str(self._get_protocol_of_identity(identity))].identity_to_time_variables(str(identity))