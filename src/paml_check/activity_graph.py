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
from paml_check.units import om_convert
from paml_check.utils import Interval
from paml_check.minimize_duration import MinimizeDuration

import pysmt
import pysmt.shortcuts

# TODO move this to a more correct location
ACTIVITY_DURATION = 'activityDuration'
ACTIVITY_STARTED_AT_TIME = 'startedAtTime'
ACTIVITY_ENDED_AT_TIME = 'endedAtTime'

def assert_type(obj, type):
    assert isinstance(obj, type), f"{obj.identity} must be of type {type.__name__}"

class ActivityGraph:
    class URI:
        def make_paml_uri(name):
            return f"http://bioprotocols.org/paml#{name}"

        Join = make_paml_uri("Join")
        Fork = make_paml_uri("Fork")
        Final = make_paml_uri("Final")
        Initial = make_paml_uri("Initial")
        Value = make_paml_uri("Value")
        AndConstraint = make_paml_uri("AndConstraint")
        OrConstraint = make_paml_uri("OrConstraint")
        XorConstraint = make_paml_uri("XorConstraint")
        NotConstraint = make_paml_uri("NotConstraint")
        Duration = make_paml_uri("Duration")
        EqualsComparison = make_paml_uri("EqualsComparison")
        LessThanComparison = make_paml_uri("LessThanComparison")
        LessThanEqualComparison = make_paml_uri("LessThanEqualComparison")
        GreaterThanComparison = make_paml_uri("GreaterThanComparison")
        GreaterThanEqualComparison = make_paml_uri("GreaterThanEqualComparison")
        Sum = make_paml_uri("SumExpression")
        Difference = make_paml_uri("DifferenceExpression")
        Product = make_paml_uri("ProductExpression")
        Constant = make_paml_uri("ConstantExpression")
        VariableExpression = make_paml_uri("VariableExpression")
        Variable = make_paml_uri("TimeVariable")
        PrimitiveExecutable = make_paml_uri("PrimitiveExecutable")

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
        self.insert_func_map = {
            self.URI.Join: self._insert_join,
            self.URI.Fork: self._insert_fork,
            self.URI.Final: self._insert_final,
            self.URI.Initial: self._insert_initial,
            self.URI.Value: self._insert_value,
            self.URI.PrimitiveExecutable: self._insert_primitive_executable,
        }
        self.constraint_func_map = {
            self.URI.AndConstraint: self._convert_and_constraint,
            self.URI.OrConstraint: self._convert_or_constraint,
            self.URI.XorConstraint: self._convert_xor_constraint,
            self.URI.NotConstraint: self._convert_not_constraint,
            self.URI.Duration: self._convert_duration_constraint,
            self.URI.EqualsComparison: self._convert_equals_constraint,
            self.URI.LessThanEqualComparison: self._convert_less_than_equals_constraint,
            self.URI.LessThanComparison: self._convert_less_than_constraint,
            self.URI.GreaterThanEqualComparison: self._convert_greater_than_equals_constraint,
            self.URI.GreaterThanComparison: self._convert_greater_than_constraint
        }
        self.expression_func_map = {
            self.URI.Sum:  self._convert_sum,
            self.URI.Difference: self._convert_difference,
            self.URI.Product: self._convert_product,
            self.URI.Constant: self._convert_constant,
            self.URI.VariableExpression: self._convert_variable_expression,
            self.URI.Variable: self._convert_variable
        }
        self.initial = None
        self.final = None
        self.nodes = {}
        self.execs = {}
        self.forks = {}
        self.joins = {}
        self.uri_to_node = {}
        self.uri_to_activity = {}
        self.protocols = {}
        self.edges = []
        self.time_constraints = {}
        self._process_doc()

        ## Variables used to link solutions back to the doc
        self.var_to_node = {} # SMT variable to graph node map
        self.node_to_var = {} # Node to SMT variable

    def _process_doc(self):
        sbol3.set_namespace('https://bbn.com/scratch/')
        protocols = self.doc.find_all(lambda obj: isinstance(obj, paml.Protocol))
        # process graph
        for protocol in protocols:
            self.protocols[protocol.identity] = protocol
            self.add_timing_properties(protocol)
            for activity in protocol.activities:
                self.insert_activity(activity)
            for flow in protocol.flows:
                self.insert_flow(flow)
        # collect time constraints
        for protocol in protocols:
            tc_ref = protocol.time_constraints
            tc = self.doc.find(tc_ref)
            self.time_constraints[protocol] = self.convert_time_constraint(tc)

    def add_timing_properties(self, variable):
        variable.start = paml.TimeVariable(
            f"{variable.identity}/{ACTIVITY_STARTED_AT_TIME}",
            time_of=variable,
            time_property=sbol3.provenance.PROV_STARTED_AT_TIME,
            value=None
        )
        variable.end = paml.TimeVariable(
            f"{variable.identity}/{ACTIVITY_ENDED_AT_TIME}",
            time_of=variable,
            time_property=sbol3.provenance.PROV_ENDED_AT_TIME,
            value=None
        )
        variable.duration = paml.Duration(
            f"{variable.identity}/{ACTIVITY_DURATION}",
            time_of=variable,
            value=None
        )
        self.doc.add(variable.start)
        self.doc.add(variable.end)
        self.doc.add(variable.duration)

        if isinstance(variable, paml.PrimitiveExecutable):
            pass
        elif isinstance(variable, paml.Protocol):
            pass
        else:
            variable.duration.value = sbol3.Measure(0.0, tyto.OM.second)

    def insert_activity(self, activity):
        """
        Inserts the activity into the graph based on the value of its type_uri
        """
        self.add_timing_properties(activity)
        type_uri = activity.type_uri
        if type_uri not in self.insert_func_map:
            raise Exception(f"insert_activity failed due to unknown activity type: {type_uri}")
        self.uri_to_activity[activity.identity] = activity
        return self.insert_func_map[type_uri](activity)

    def insert_flow(self, flow):
        # we could find the original objects through self.doc.find
        # but it is probably faster to just use the dictionary lookup
        # in self.nodes for the uri of both source and sink.
        source_id = str(flow.source)
        sink_id = str(flow.sink)
        source = self.uri_to_activity[source_id]
        sink = self.uri_to_activity[sink_id]
        start = source.end
        end = sink.start
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

    def _measure_to_time(self, meas):
        return om_convert(meas.value, meas.unit, tyto.OM.second)

    def convert_time_constraint(self, constraint):
        """
        Convert a paml specification of a constraint into a formula.
        :param constraint:
        :return: pysmt formula
        """
        type_uri = constraint.type_uri
        if type_uri not in self.constraint_func_map:
            raise Exception(f"convert_time_constraint failed due to unknown constraint type: {type_uri}")
        return self.constraint_func_map[type_uri](constraint)

    def _convert_and_constraint(self, constraint):
        clauses = [ self.convert_time_constraint(clause)
                    for clause in constraint.clause ]
        return pysmt.shortcuts.And(clauses)

    def _convert_or_constraint(self, constraint):
        clauses = [ self.convert_time_constraint(clause)
                    for clause in constraint.clause ]
        return pysmt.shortcuts.Or(clauses)

    def _convert_xor_constraint(self, constraint):
        clauses = [ self.convert_time_constraint(clause)
                    for clause in constraint.clause ]
        return pysmt.shortcuts.ExactlyOne(clauses)

    def _convert_not_constraint(self, constraint):
        clause = self.convert_time_constraint(constraint.clause)
        return pysmt.shortcuts.Not(clause)

    def _convert_duration_constraint(self, constraint):
        activity = self.uri_to_activity[constraint.time_of.identity]
        duration = self._measure_to_time(constraint.value)
        clause = binary_temporal_constraint(
            pysmt.shortcuts.Symbol(activity.start.identity, pysmt.shortcuts.REAL),
            [[duration, duration]],
            pysmt.shortcuts.Symbol(activity.end.identity, pysmt.shortcuts.REAL))
        return clause

    def _convert_equals_constraint(self, constraint):
        term1 = self._convert_expression(self.doc.find(constraint.term1))
        term2 = self._convert_expression(self.doc.find(constraint.term2))
        clause = pysmt.shortcuts.Equals(term1, term2)
        return clause

    def _convert_less_than_equals_constraint(self, constraint):
        term1 = self._convert_expression(self.doc.find(constraint.term1))
        term2 = self._convert_expression(self.doc.find(constraint.term2))
        clause = pysmt.shortcuts.LE(term1, term2)
        return clause

    def _convert_less_than_constraint(self, constraint):
        term1 = self._convert_expression(self.doc.find(constraint.term1))
        term2 = self._convert_expression(self.doc.find(constraint.term2))
        clause = pysmt.shortcuts.LT(term1, term2)
        return clause

    def _convert_greater_than_equals_constraint(self, constraint):
        term1 = self._convert_expression(self.doc.find(constraint.term1))
        term2 = self._convert_expression(self.doc.find(constraint.term2))
        clause = pysmt.shortcuts.GE(term1, term2)
        return clause

    def _convert_greater_than_constraint(self, constraint):
        term1 = self._convert_expression(self.doc.find(constraint.term1))
        term2 = self._convert_expression(self.doc.find(constraint.term2))
        clause = pysmt.shortcuts.GT(term1, term2)
        return clause


    def _convert_expression(self, expression):
        type_uri = expression.type_uri
        if type_uri not in self.expression_func_map:
            raise Exception(f"convert_expression failed due to unknown expression type: {type_uri}")
        return self.expression_func_map[type_uri](expression)

    def _convert_sum(self, expression):
        term1 = self._convert_expression(self.doc.find(expression.term1))
        term2 = self._convert_expression(self.doc.find(expression.term2))
        clause = pysmt.shortcuts.Plus(term1, term2)
        return clause

    def _convert_difference(self, expression):
        term1 = self._convert_expression(self.doc.find(expression.term1))
        term2 = self._convert_expression(self.doc.find(expression.term2))
        clause = pysmt.shortcuts.Minus(term1, term2)
        return clause

    def _convert_product(self, expression):
        term1 = self._convert_expression(self.doc.find(expression.term1))
        term2 = self._convert_expression(self.doc.find(expression.term2))
        clause = pysmt.shortcuts.Times(term1, term2)
        return clause

    def _convert_constant(self, expression):
        term = pysmt.shortcuts.Real(self._measure_to_time(expression.term))
        return term

    def _convert_variable(self, variable):
        activity = variable.time_of
        if ACTIVITY_ENDED_AT_TIME in variable.time_property:
            var = activity.end
        elif ACTIVITY_STARTED_AT_TIME in variable.time_property:
            var = activity.start

        clause = pysmt.shortcuts.Symbol(var.identity, pysmt.shortcuts.REAL)
        return clause

    def _convert_variable_expression(self, expression):
        clause = self._convert_expression(self.doc.find(expression.term))
        return clause

    def _insert_variable(self, variable, type = None):
        if type is not None:
            assert_type(variable, paml.TimeVariable)
        uri = variable.identity
        self.nodes[uri] = variable
        self.uri_to_node[uri] = variable
        return variable

    def _insert_time_range(self, activity, min_d):
        # collect start, end, and duration variables
        start = self._insert_variable(activity.start)
        end = self._insert_variable(activity.end)
        # duration = self._insert_variable(activity.duration, paml.TimeVariable)
        duration = activity.duration
        # the values of each TimeVariable are a Measure
        start_measure = start.value
        end_measure = end.value
        duration_measure = duration.value
        # determine the intersected interval
        difference = [[min_d, math.inf]]
        if duration_measure:
            difference.append([duration_measure.value, duration_measure.value])
        if start_measure and end_measure:
            d = end_measure.value - start_measure.value
            difference.append([d, d])
        intersected_difference = Interval.intersect(difference)
        # store the TimeVariables and the intersected difference as an edge
        self.edges.append((start, [intersected_difference], end))
        return start, end, duration

    def _insert_executable(self, activity):
        start, end, _ = self._insert_time_range(activity, self.epsilon)
        assert hasattr(activity, 'input'), f"_insert_exec_node failed. No input pins found on: {activity.identity}"
        assert hasattr(activity, 'output'), f"_insert_exec_node failed. No output pins found on: {activity.identity}"
        for input in activity.input:
            self.uri_to_node[input.identity] = start
            self.uri_to_activity[input.identity] = activity
        for output in activity.output:
            self.uri_to_node[output.identity] = end
            self.uri_to_activity[output.identity] = activity

    def _insert_join(self, activity):
        start, end, _ = self._insert_time_range(activity, 0)
        self.joins[start.identity] = activity
        return start, end

    def _insert_fork(self, activity):
        start, end, _ = self._insert_time_range(activity, 0)
        self.forks[end.identity] = activity
        return start, end

    def _insert_initial(self, activity):
        # Initial is a specialized fork
        start, _ = self._insert_fork(activity)
        # FIXME is this a true limitation?
        if self.initial is not None:
            raise Exception("Cannot support multiple Initial nodes in graph")
        self.initial = start

    def _insert_final(self, activity):
        # Final is a specialized join
        _, end = self._insert_join(activity)
        # FIXME is this a true limitation?
        if self.final is not None:
            raise Exception("Cannot support multiple Final nodes in graph")
        self.final = end

    def _insert_value(self, activity):
        self._insert_time_range(activity, 0)

    def _insert_primitive_executable(self, activity):
        self._insert_executable(activity)


    def find_fork_groups(self):
        fork_groups = {f: [] for f in self.forks}
        for (start, _, end) in self.edges:
            start_id = start.identity
            if start_id in fork_groups:
                fork_groups[start_id].append(end)
        return fork_groups

    def find_join_groups(self):
        join_groups = {j: [] for j in self.joins}
        for (start, _, end) in self.edges:
            end_id = end.identity
            if end_id in join_groups:
                join_groups[end_id].append(start)
        return join_groups

    def print_debug(self):
        try:
            print("URI to node map")
            for uri in self.uri_to_node:
                print(f"  {uri} : {self.uri_to_node[uri]}")
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
                    print(f"    - {join.identity}")
            print("----------------")

            print("Forks")
            fork_groups = self.find_fork_groups()
            for f in fork_groups:
                print(f"  {f}")
                for fork in fork_groups[f]:
                    print(f"    - {fork.identity}")
            print("----------------")

            print("Edges")
            for pair in self.edges:
                print(f"  {pair[0].identity} ---> {pair[2].identity}")
            print("----------------")

            print("Durations")
            handled = []
            for _, activity in self.uri_to_activity.items():
                id = activity.identity
                if hasattr(activity, "duration") and \
                hasattr(activity.duration, "value") and \
                hasattr(activity.duration.value, "value"):
                        if id not in handled:
                            handled.append(id)
                            print(f"  {id} : {activity.duration.value.value}")
                else:
                    print(f"  {id} : N/A")
            print("----------------")
        except Exception as e:
            print("Error during print_debug: " + e)

    def generate_constraints(self):
        # treat each node identity (uri) as a timepoint
        timepoints = list(self.nodes.keys())

        timepoint_vars = {t: pysmt.shortcuts.Symbol(t, pysmt.shortcuts.REAL)
                          for t in timepoints}

        self.var_to_node = { v: k for k, v in timepoint_vars.items() }
        self.node_to_var = {k: v for k, v in timepoint_vars.items()}

        protocol_constraints = self._make_protocol_constraints(timepoint_vars)

        timepoint_var_domains = [pysmt.shortcuts.And(pysmt.shortcuts.GE(t, pysmt.shortcuts.Real(0.0)),
                                                     pysmt.shortcuts.LE(t, pysmt.shortcuts.Real(self.infinity)))
                                 for _, t in timepoint_vars.items()]

        time_constraints = [binary_temporal_constraint(timepoint_vars[start.identity],
                                                       Interval.substitute_infinity(self.infinity, disjunctive_distance),
                                                       timepoint_vars[end.identity])
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
            protocol_start_id = protocol.start.identity
            protocol_end_id = protocol.end.identity

            protocol_start_var = pysmt.shortcuts.Symbol(protocol_start_id,
                                                        pysmt.shortcuts.REAL)
            protocol_end_var = pysmt.shortcuts.Symbol(protocol_end_id,
                                                      pysmt.shortcuts.REAL)

            self.var_to_node[protocol_start_var] = protocol_start_id
            self.var_to_node[protocol_end_var] = protocol_end_id


            initial_node = protocol.initial()
            initial_start = initial_node.start
            start_constraint = pysmt.shortcuts.Equals(protocol_start_var,
                                                      timepoint_vars[initial_start.identity])
            protocol_start_constraints.append(start_constraint)

            final_node = protocol.final()
            final_end = final_node.end
            end_constraint = pysmt.shortcuts.Equals(protocol_end_var,
                                                      timepoint_vars[final_end.identity])
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

        for _, activity in self.uri_to_activity.items():
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