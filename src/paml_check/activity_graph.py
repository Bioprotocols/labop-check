from logging import warning
import math
import paml
import sbol3
import tyto
import uml

from paml_check.constraints import \
    binary_temporal_constraint, \
    join_constraint, \
    unary_temporal_constaint, \
    anytime_before, \
    determine_time_constraint, \
    duration_constraint
from paml_check.units import om_convert
from paml_check.utils import Interval
from paml_check.minimize_duration import MinimizeDuration
from paml_check.convert_constraints import ConstraintConverter
from paml_check.solver_variable import \
    define_solver_variable, \
    get_solver_variables, \
    debug_solver_variables
from paml_check.solver_variable import SolverVariableConstants as svc

import paml_time as pamlt # May be unused but is required to access paml_time values

import pysmt
import pysmt.shortcuts

def assert_type(obj, type):
    assert isinstance(obj, type), f"{obj.identity} must be of type {type.__name__}"

class ActivityGraph:

    def __init__(self, doc: sbol3.Document, epsilon=0.0001, infinity=10e10, destructive=False):
        if destructive:
            self.doc = doc
        else:
            # TODO there may be a more efficient way to clone a sbol3 Document
            # write the original doc to a string and then read it in as a new doc
            self.doc = sbol3.Document()
            self.doc.read_string(doc.write_string('ttl'), 'ttl')

        self.epsilon = epsilon
        self.infinity = infinity
        # function handling for node types
        self.node_func_map = {
            uml.JoinNode: self._insert_join,
            uml.ForkNode: self._insert_fork,
            uml.FinalNode: self._insert_final,
            uml.InitialNode: self._insert_initial,
            # uml.CallBehaviorAction: self._insert_call_behavior_action
        }

        self.variables = {}

        self.nodes = {}
        self.execs = {}

        # Control Nodes
        self.forks= {}
        self.joins = {}
        self.initial = {}
        self.final = {}

        self.uri_to_node = {}
        self.identity_to_node = {}
        self.protocols = {}
        self.edges = []
        self.time_constraints = {}
        self._process_doc()

        ## Variables used to link solutions back to the doc
        self.var_to_node = {} # SMT variable to graph node map
        self.node_to_var = {} # Node to SMT variable

    def define_variable(self, name, ref):
        # build a simple map of the variable name back to the variable
        var = define_solver_variable(name, ref)
        self.variables[var.name] = var
        return var

    def get_variable(self, name):
        if name not in self.variables:
            raise Exception(f"Variable with name '{name}' does not exist")
        return self.variables[name]

    def _process_doc(self):
        sbol3.set_namespace('https://bbn.com/scratch/')
        protocols = self.doc.find_all(lambda obj: isinstance(obj, paml.Protocol))

        # process graph
        for protocol in protocols:
            self._process_protocol(protocol)

        # collect time constraints
        for protocol in protocols:
            self.time_constraints[protocol.identity] = self.extract_time_constraints(protocol)

    # TODO this is a bit too much of a hack for my liking
    def _process_protocol(self, protocol):
        if protocol.identity in self.protocols:
            warning(f"Found duplicate protocol reference for {protocol.identity} while processing. Skipping...")
            return
        print(f"Processing protocol: {protocol.identity}")
        self.protocols[protocol.identity] = protocol
        def apply(target):
            self.define_variable(svc.START_TIME_VARIABLE, target)
            self.define_variable(svc.END_TIME_VARIABLE, target)
            self.define_variable(svc.DURATION_VARIABLE, target)
            self.identity_to_node[target.identity] = target
            self.nodes[target.identity] = target
        # FIXME there is something odd going on with initial and final instances
        apply(protocol.initial())
        apply(protocol.final())
        for node in protocol.nodes:
            apply(node)
            # t = type(node)
            # if t not in self.node_func_map:
            #     warning(f"Skipping processing of node {node.identity}. No handler function found.")
            #     continue
            # self.node_func_map[t](protocol, node)
        for edge in protocol.edges:
            source_id = str(edge.source)
            target_id = str(edge.target)
            source = self.get_node_for_identity(source_id)
            target = self.get_node_for_identity(target_id)
            self.insert_edge(source, target)
        self.repair_nodes_with_no_in_flow(protocol)
        self.repair_nodes_with_no_out_flow(protocol)
        apply(protocol)

    # HACK to get around pins not holding any reference information
    # to find their parent node
    def get_node_for_identity(self, identity: str):
        org_identity = str(identity)
        while identity not in self.identity_to_node:
            res = identity.rsplit('/', 1)
            if len(res) == 1:
                break
            identity = res[0]
        if identity not in self.identity_to_node:
            raise Exception(f"Failed to find node for {org_identity}")
        return self.identity_to_node[identity]
        

    def extract_time_constraints(self, protocol):
        cc = ConstraintConverter()
        doc = protocol.document
        count = len(protocol.time_constraints)

        # no constraints were specified
        if count == 0:
            # FIXME what shortcut is approriate to return when no constraints are specified?
            return pysmt.shortcuts.TRUE()

        # exactly one constraint was specified
        if count == 1:
            tc = doc.find(protocol.time_constraints[0])
            return cc.convert_constraint(tc)

        # more than one constraint was specified
        # so fallback to an implicit And
        warning(f"Protocol with identity '{protocol.indentity}' provided multiple top level constraints."
                + "\n  These will be treated as an implicit And operation. This is not recommended.")
        clauses = [ cc.convert_constraint(doc.find(tc_ref))
                    for tc_ref in protocol.time_constraints ]
        return pysmt.shortcuts.And(clauses)


    # def add_timing_properties(self, variable):
    #     variable.start = paml.TimeVariable(
    #         f"{variable.identity}/{ACTIVITY_STARTED_AT_TIME}",
    #         time_of=variable,
    #         time_property=sbol3.provenance.PROV_STARTED_AT_TIME,
    #         value=None
    #     )
    #     variable.end = paml.TimeVariable(
    #         f"{variable.identity}/{ACTIVITY_ENDED_AT_TIME}",
    #         time_of=variable,
    #         time_property=sbol3.provenance.PROV_ENDED_AT_TIME,
    #         value=None
    #     )
    #     variable.duration = paml.Duration(
    #         f"{variable.identity}/{ACTIVITY_DURATION}",
    #         time_of=variable,
    #         value=None
    #     )
    #     self.doc.add(variable.start)
    #     self.doc.add(variable.end)
    #     self.doc.add(variable.duration)

    #     if isinstance(variable, paml.PrimitiveExecutable):
    #         pass
    #     elif isinstance(variable, paml.Protocol):
    #         pass
    #     else:
    #         variable.duration.value = sbol3.Measure(0.0, tyto.OM.second)

    # def insert_activity(self, activity):
    #     """
    #     Inserts the activity into the graph based on the value of its type_uri
    #     """
    #     self.add_timing_properties(activity)
    #     type_uri = activity.type_uri
    #     if type_uri not in self.insert_func_map:
    #         raise Exception(f"insert_activity failed due to unknown activity type: {type_uri}")
    #     self.identity_to_node[activity.identity] = activity
    #     return self.insert_func_map[type_uri](activity)

    def insert_edge(self, source, target):
        # we could find the original objects through self.doc.find
        # but it is probably faster to just use the dictionary lookup
        # in self.nodes for the uri of both source and sink.
        source_vars = get_solver_variables(source)
        target_vars = get_solver_variables(target)

        start = source_vars.end
        end = target_vars.start
        # TimeVariable to Measure
        start_measure = start.value
        end_measure = end.value
        # This constraint assumes that it connects a source's end time to a sink's start time
        difference = [[0.0, math.inf]]
        if start_measure and end_measure:
            d = end_measure.value - start_measure.value
            difference.append([d, d])
        intersected_difference = Interval.intersect(difference)

        # store the TimeVariables and the intersected difference as an edge
        self.edges.append((start, [intersected_difference], end))

    

    def repair_nodes_with_no_out_flow(self, protocol):
        final = protocol.final()
        results = []
        for node in protocol.nodes:
            found = False
            for edge in self.edges:
                if edge[0].ref == node:
                    found = True
                    break
            if found is False:
                results.append(node)
        if len(results) > 0:
            warning("Repairing out flow")
            for result in results:
                if isinstance(result, uml.InitialNode):
                    continue
                if isinstance(result, uml.FlowFinalNode):
                    continue
                warning(f"  {result.identity}--->{final.identity}")
                self.insert_edge(result, final)


    def repair_nodes_with_no_in_flow(self, protocol):
        initial = protocol.initial()
        results = []
        for node in protocol.nodes:
            found = False
            for edge in self.edges:
                if edge[2].ref == node:
                    found = True
                    break
            if found is False:
                results.append(node)
        if len(results) > 0:
            warning("Repairing in flow")
            for result in results:
                if isinstance(result, uml.InitialNode):
                    continue
                if isinstance(result, uml.FlowFinalNode):
                    continue
                warning(f"  {initial.identity}--->{result.identity}")
                self.insert_edge(initial, result)

                    

    # def _insert_variable(self, variable, type = None):
    #     if type is not None:
    #         assert_type(variable, paml.TimeVariable)
    #     uri = variable.identity
    #     self.nodes[uri] = variable
    #     self.uri_to_node[uri] = variable
    #     return variable

    # def _insert_time_range(self, activity, min_d):
    #     # collect start, end, and duration variables
    #     start = self._insert_variable(activity.start)
    #     end = self._insert_variable(activity.end)
    #     # duration = self._insert_variable(activity.duration, paml.TimeVariable)
    #     duration = activity.duration
    #     # the values of each TimeVariable are a Measure
    #     start_measure = start.value
    #     end_measure = end.value
    #     duration_measure = duration.value
    #     # determine the intersected interval
    #     difference = [[min_d, math.inf]]
    #     if duration_measure:
    #         difference.append([duration_measure.value, duration_measure.value])
    #     if start_measure and end_measure:
    #         d = end_measure.value - start_measure.value
    #         difference.append([d, d])
    #     intersected_difference = Interval.intersect(difference)
    #     # store the TimeVariables and the intersected difference as an edge
    #     self.edges.append((start, [intersected_difference], end))
    #     return start, end, duration

    # def _insert_executable(self, activity):
    #     start, end, _ = self._insert_time_range(activity, self.epsilon)
    #     assert hasattr(activity, 'input'), f"_insert_exec_node failed. No input pins found on: {activity.identity}"
    #     assert hasattr(activity, 'output'), f"_insert_exec_node failed. No output pins found on: {activity.identity}"
    #     for input in activity.input:
    #         self.uri_to_node[input.identity] = start
    #         self.identity_to_node[input.identity] = activity
    #     for output in activity.output:
    #         self.uri_to_node[output.identity] = end
    #         self.identity_to_node[output.identity] = activity

    def _insert_join(self, protocol, node):
        start = get_solver_variables(node).start
        self.joins[start] = node

    def _insert_fork(self, protocol, node):
        end = get_solver_variables(node).end
        self.forks[end] = node

    def _insert_initial(self, protocol, node):
        # Initial is a specialized fork
        self.initial[protocol.identity] = node
        self._insert_fork(node)

    def _insert_final(self, protocol, node):
        # Final is a specialized join
        self.final[protocol.identity] = node
        self._insert_join(node)

    # def _insert_value(self, activity):
    #     self._insert_time_range(activity, 0)

    # def _insert_primitive_executable(self, activity):
    #     self._insert_executable(activity)


    def find_fork_groups(self):
        fork_groups = {f: [] for f in self.forks}
        for (start, _, end) in self.edges:
            start_id = start.name
            if start_id in fork_groups:
                fork_groups[start_id].append(end)
        return fork_groups

    def find_join_groups(self):
        join_groups = {j: [] for j in self.joins}
        for (start, _, end) in self.edges:
            end_id = end.name
            if end_id in join_groups:
                join_groups[end_id].append(start)
        return join_groups

    def print_debug(self):
        try:
            # print("URI to node map")
            # for uri in self.uri_to_node:
            #     print(f"  {uri} : {self.uri_to_node[uri]}")
            # print("----------------")

            # print("Executable activities")
            # for exec in self.execs:
            #     print(f"  {exec}")
            # print("----------------")

            print("Nodes")
            for _, node in self.nodes.items():
                debug_solver_variables(node)
            print("----------------")

            print("Joins")
            join_groups = self.find_join_groups()
            for j in join_groups:
                print(f"  {j}")
                for join in join_groups[j]:
                    print(f"    - {join.name}")
            print("----------------")

            print("Forks")
            fork_groups = self.find_fork_groups()
            for f in fork_groups:
                print(f"  {f}")
                for fork in fork_groups[f]:
                    print(f"    - {fork.name}")
            print("----------------")

            print("Edges")
            for edge in self.edges:
                print(f"  {edge[0].name} ---> {edge[2].name}")
            print("----------------")

            print("Variables")
            for _, variable in self.variables.items():
                print(f"  {variable.name} ---> {variable.value}")
            print("----------------")
            # print("Durations")
            # handled = []
            # for _, activity in self.identity_to_node.items():
            #     id = activity.identity
            #     if hasattr(activity, "duration") and \
            #     hasattr(activity.duration, "value") and \
            #     hasattr(activity.duration.value, "value"):
            #             if id not in handled:
            #                 handled.append(id)
            #                 print(f"  {id} : {activity.duration.value.value}")
            #     else:
            #         print(f"  {id} : N/A")
            # print("----------------")
        except Exception as e:
            print(f"Error during print_debug: {e}")

    def generate_constraints(self):
        # treat each node identity (uri) as a timepoint
        timepoints = list(self.variables.keys())

        timepoint_vars = {t: pysmt.shortcuts.Symbol(t, pysmt.shortcuts.REAL)
                          for t in timepoints}

        self.var_to_node = { v: k for k, v in timepoint_vars.items() }
        self.node_to_var = {k: v for k, v in timepoint_vars.items()}

        protocol_constraints = self._make_protocol_constraints(timepoint_vars)

        timepoint_var_domains = [pysmt.shortcuts.And(pysmt.shortcuts.GE(t, pysmt.shortcuts.Real(0.0)),
                                                     pysmt.shortcuts.LE(t, pysmt.shortcuts.Real(self.infinity)))
                                 for _, t in timepoint_vars.items()]

        time_constraints = [binary_temporal_constraint(timepoint_vars[start.name],
                                                       Interval.substitute_infinity(self.infinity, disjunctive_distance),
                                                       timepoint_vars[end.name])
                            for (start, disjunctive_distance, end) in self.edges]

        join_constraints = []                     
        join_groups = self.find_join_groups()
        for id, grp in join_groups.items():
            join_constraints.append(
                join_constraint(
                    timepoint_vars[id],
                    [timepoint_vars[tp.identity] for tp in grp]
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

        given_constraints = pysmt.shortcuts.And(timepoint_var_domains + \
                                                time_constraints + \
                                                join_constraints + \
                                                protocol_constraints + \
                                                list(self.time_constraints.values())
            )

        return given_constraints

    def _make_protocol_constraints(self, timepoint_vars):
        """
        Add constraints that:
         - link initial to protocol start
         - link final to protocol end
        :return:
        """
        protocol_start_constraints = []
        protocol_end_constraints = []

        for _, protocol in self.protocols.items():
            pvrs = get_solver_variables(protocol)
            protocol_start_id = pvrs.start.name
            protocol_end_id = pvrs.end.name

            protocol_start_var = pysmt.shortcuts.Symbol(protocol_start_id,
                                                        pysmt.shortcuts.REAL)
            protocol_end_var = pysmt.shortcuts.Symbol(protocol_end_id,
                                                      pysmt.shortcuts.REAL)

            self.var_to_node[protocol_start_var] = protocol_start_id
            self.var_to_node[protocol_end_var] = protocol_end_id


            initial_node = protocol.initial()
            ivrs = get_solver_variables(initial_node)
            initial_start = ivrs.start
            start_constraint = pysmt.shortcuts.Equals(protocol_start_var,
                                                      timepoint_vars[initial_start.name])
            protocol_start_constraints.append(start_constraint)

            final_node = protocol.final()
            fvrs = get_solver_variables(final_node)
            final_end = fvrs.end
            end_constraint = pysmt.shortcuts.Equals(protocol_end_var,
                                                      timepoint_vars[final_end.name])
            protocol_end_constraints.append(end_constraint)

        return  protocol_start_constraints + protocol_end_constraints


    def add_result(self, doc, result):
        if result:
            for var, value in result:
                v = float(value.constant_value())
                graph_node = self.var_to_node[var]
                doc_node = doc.find(graph_node) # FIXME use the self.uri_to_node, but fix it to include all the nodes
                doc_node.value = sbol3.Measure(v, tyto.OM.time)

        return doc

    def get_end_time_var(self, protocol):
        return self.node_to_var[self.protocols[protocol].final().end.identity]

    def get_duration(self, model, protocol):
        """
        Get the duration of protocol represented by model
        :param model:
        :return: value
        """
        duration = None
        if model:
            final_node_end_var = self.get_end_time_var(protocol)
            duration = float(model[final_node_end_var].constant_value())
        return duration


    def compute_durations(self, doc):
        """
        Use start and end times on activities to compute their durations,
        including the overall protocol duration.
        :param doc:
        :return: doc
        """

        def calculate_duration(elt):
            return sbol3.Measure(elt.end.value.value - elt.start.value.value,
                                 tyto.OM.time)

        for _, protocol in self.protocols.items():
            # set protocol start and end times
            protocol.start.value = sbol3.Measure(protocol.initial().start.value.value, tyto.OM.time)
            protocol.end.value = sbol3.Measure(protocol.final().end.value.value, tyto.OM.time)
            protocol.duration.value = calculate_duration(protocol)

        for _, activity in self.identity_to_node.items():
            if hasattr(activity, "duration") and \
               hasattr(activity, "start") and \
               hasattr(activity.start, "value") and \
               hasattr(activity, "end") and \
               hasattr(activity.end, "value"):
                activity.duration.value = calculate_duration(activity)
        return doc

    def get_minimum_duration(self):
        """
        Find the minimum duration for the protocol.
        Solver is SMT, so do a binary search on the duration bound.
        :return: minimum duration
        """

        base_formula = self.generate_constraints()
        result = pysmt.shortcuts.get_model(base_formula)
        min_duration = {protocol: None for protocol in self.protocols}
        if result:
            for protocol in self.protocols:
                supremum_duration = self.get_duration(result, protocol)
                min_duration[protocol] = MinimizeDuration(base_formula, self, protocol).minimize(supremum_duration)

        return min_duration