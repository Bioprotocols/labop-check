import paml_check.convert_constraints as pcc
import paml_time as pamlt
import pysmt
import pysmt.shortcuts

# FIXME all of these functions still need to updates to work with the new uml changes

def convert_equals_constraint(converter: 'pcc.ConstraintConverter',
                              constraint):
    term1 = converter.convert_expression(constraint.document.find(constraint.term1))
    term2 = converter.convert_expression(constraint.document.find(constraint.term2))
    clause = pysmt.shortcuts.Equals(term1, term2)
    return clause

def convert_less_than_equals_constraint(converter: 'pcc.ConstraintConverter',
                                        constraint):
    term1 = converter.convert_expression(constraint.document.find(constraint.term1))
    term2 = converter.convert_expression(constraint.document.find(constraint.term2))
    clause = pysmt.shortcuts.LE(term1, term2)
    return clause

def convert_less_than_constraint(converter: 'pcc.ConstraintConverter',
                                 constraint):
    term1 = converter.convert_expression(constraint.document.find(constraint.term1))
    term2 = converter.convert_expression(constraint.document.find(constraint.term2))
    clause = pysmt.shortcuts.LT(term1, term2)
    return clause

def convert_greater_than_equals_constraint(converter: 'pcc.ConstraintConverter',
                                           constraint):
    term1 = converter.convert_expression(constraint.document.find(constraint.term1))
    term2 = converter.convert_expression(constraint.document.find(constraint.term2))
    clause = pysmt.shortcuts.GE(term1, term2)
    return clause

def convert_greater_than_constraint(converter: 'pcc.ConstraintConverter',
                                    constraint):
    term1 = converter.convert_expression(constraint.document.find(constraint.term1))
    term2 = converter.convert_expression(constraint.document.find(constraint.term2))
    clause = pysmt.shortcuts.GT(term1, term2)
    return clause