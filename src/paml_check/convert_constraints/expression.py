import paml_check.convert_constraints as pcc
import paml_time as pamlt
import pysmt
import pysmt.shortcuts

# FIXME all of these functions still need to updates to work with the new uml changes

def convert_sum(converter: 'pcc.ConstraintConverter', expression):
    term1 = converter.convert_expression(expression.document.find(expression.term1))
    term2 = converter.convert_expression(expression.document.find(expression.term2))
    clause = pysmt.shortcuts.Plus(term1, term2)
    return clause

def convert_difference(converter: 'pcc.ConstraintConverter', expression):
    term1 = converter.convert_expression(expression.document.find(expression.term1))
    term2 = converter.convert_expression(expression.document.find(expression.term2))
    clause = pysmt.shortcuts.Minus(term1, term2)
    return clause

def convert_product(converter: 'pcc.ConstraintConverter', expression):
    term1 = converter.convert_expression(expression.document.find(expression.term1))
    term2 = converter.convert_expression(expression.document.find(expression.term2))
    clause = pysmt.shortcuts.Times(term1, term2)
    return clause

def convert_constant(converter: 'pcc.ConstraintConverter', expression):
    term = pysmt.shortcuts.Real(converter.measure_to_time(expression.term))
    return term

# def convert_variable(converter: 'pcc.ConstraintConverter', variable):
#     activity = variable.time_of
#     if ACTIVITY_ENDED_AT_TIME in variable.time_property:
#         var = activity.end
#     elif ACTIVITY_STARTED_AT_TIME in variable.time_property:
#         var = activity.start
#     clause = pysmt.shortcuts.Symbol(var.identity, pysmt.shortcuts.REAL)
#     return clause

def convert_variable_expression(converter: 'pcc.ConstraintConverter', expression):
    clause = converter.convert_expression(expression.document.find(expression.term))
    return clause