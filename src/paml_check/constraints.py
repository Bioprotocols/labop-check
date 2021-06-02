"""
Definitions of constraints
"""

import pysmt


def binary_temporal_constraint(t_1, disjunctive_distance, t_2):
    """
    Difference between t_2 and t_1 is within one of the disjunctive intervals
    :param t_1:
    :param disjunctive_distance:
    :param t_2:
    :return:
    """
    difference = pysmt.shortcuts.Minus(t_2, t_1)
    constraint = pysmt.shortcuts.Or([
        pysmt.shortcuts.And(pysmt.shortcuts.GE(difference, pysmt.shortcuts.Real(dd[0])),
                            pysmt.shortcuts.LE(difference, pysmt.shortcuts.Real(dd[1])))
        for dd in disjunctive_distance
    ])
    return constraint


def unary_temporal_constaint(t_p, disjunctive_distance):
    """
    The abolute time of tp is within one of the disjunctive intervals
    :param t_p:
    :param disjunctive_distance:
    :return:
    """
    constraint = pysmt.shortcuts.Or([
        pysmt.shortcuts.And(pysmt.shortcuts.GE(t_p, pysmt.shortcuts.Real(dd[0])),
                            pysmt.shortcuts.LE(t_p, pysmt.shortcuts.Real(dd[1])))
        for dd in disjunctive_distance
    ])
    return constraint


def join_constraint(t_join, joined_times):
    """
    A join step must be equal to one of the preceding timepoints
    :param t_join:
    :param joined_times:
    :return:
    """
    constraint = pysmt.shortcuts.Or([
        pysmt.shortcuts.Equals(t_join, t_j)
        for t_j in joined_times
    ])
    return constraint


def time_points_happen_once_constraint(timepoint_vars, happenings):
    """
    Each time point is equal to at least one happening
    :param timepoint_vars:
    :param happenings:
    :return: constraint
    """
    constraint = pysmt.shortcuts.And([
        pysmt.shortcuts.Or([
            pysmt.shortcuts.Equals(t, h)
            for h in happenings
        ])
        for _, t in timepoint_vars.items()
    ])
    return constraint

def duration_constraint(start, end, duration):
    #constraint = pysmt.shortcuts.Equals(duration,
    #                              pysmt.shortcuts.Minus(end, start))
    constraint = pysmt.shortcuts.And(pysmt.shortcuts.LE(duration,
                                                            pysmt.shortcuts.Minus(end, start)),
                                     pysmt.shortcuts.GE(duration,
                                                             pysmt.shortcuts.Minus(end, start)))

    return constraint

def anytime_before(t1, t2):
    return [[0,t_inf]]



def determine_time_constraint(source_uri, disjunctive_distance, sink_uri):
    t1 = timepoint_vars[source_uri]
    t2 = timepoint_vars[sink_uri]
    return binary_temporal_constraint(t1, disjunctive_distance, t2)