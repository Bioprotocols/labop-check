from logging import warning
import uml
import paml_time as pamlt
import pysmt
import tyto

# from paml_check.constraints import \
#     binary_temporal_constraint, \
#     join_constraint, \
#     unary_temporal_constaint, \
#     anytime_before, \
#     determine_time_constraint, \
#     duration_constraint
# from paml_check.utils import Interval

from paml_check.units import om_convert
from . import \
    comparison, \
    duration, \
    expression, \
    logic, \
    time

class ConstraintConverter:
    def __init__(self):
        self.constraint_func_map = {
            pamlt.AndConstraint: logic.convert_and_constraint,
            pamlt.OrConstraint: logic.convert_or_constraint,
            pamlt.XorConstraint: logic.convert_xor_constraint,
            uml.DurationConstraint: duration.convert_duration_constraint,
            uml.TimeConstraint: time.convert_time_constraint,
            # pamlt.EqualsComparison: comparison.convert_equals_constraint,
            # pamlt.LessThanEqualsComparison: comparison.convert_less_than_equals_constraint,
            # pamlt.LessThanComparison: comparison.convert_less_than_constraint,
            # pamlt.GreaterThanEqualComparison: comparison.convert_greater_than_equals_constraint,
            # pamlt.GreaterThanComparison: comparison.convert_greater_than_constraint
        }
        self.expression_func_map = {
            # pamlt.Sum:  expression.convert_sum,
            # pamlt.Difference: expression.convert_difference,
            # pamlt.Product: expression.convert_product,
            # pamlt.Constant: expression.convert_constant,
            # pamlt.VariableExpression: expression.convert_variable_expression,
            # pamlt.Variable: expression.convert_variable
        }

    def time_measure_to_seconds(self, meas):
        return om_convert(meas.value, meas.unit, tyto.OM.second)
    
    def _convert_constraint_by_type(self, constraint):
        # FIXME require that constraints always apply to some elements?
        # assert(len(constraint.constrained_elements) > 0)
        t = type(constraint)
        if t not in self.constraint_func_map:
            raise Exception(f"_convert_constraint_by_type failed due to unknown constraint type: {t}")
        return self.constraint_func_map[t](self, constraint)

    def _convert_expression_by_type(self, expression):
        t = type(expression)
        if t not in self.expression_func_map:
            raise Exception(f"_convert_expression_by_type failed due to unknown expression type: {t}")
        return self.expression_func_map[t](self, expression)

    def convert_constraint(self, constraint):
        if isinstance(constraint, list):
            if len(constraint) > 1:
                warning(f"Treating list of constraints as an implicit And (for {constraint.indentity})."
                        + "\n  This is not recommended.")
                clauses = [ self._convert_constraint_by_type(c)
                            for c in constraint ]
                return pysmt.shortcuts.And(clauses)
            else:
                # FIXME this may just be fine to leave as real functionality but for now print a warning
                warning(f"Treating list of constraints of length one as a single constraint (for {constraint.indentity}).")
                constraint = constraint[0]
        return self._convert_constraint_by_type(constraint)

    def convert_expression(self, expression):
        # TODO
        return self._convert_expression_by_type(expression)

                