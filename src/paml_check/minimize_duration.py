"""
Helper to minimize duration of protocol
"""

import pysmt

class MinimizeDuration():
    """
    Helper class to find minimum duration for a protocol
    """

    def __init__(self, base_formula, graph, protocol, threshold=0.1):
        """
        Initialize variables for the search
        :param base_formula:
        :param graph:
        :param protocol:
        :param threshold:
        """
        self.graph = graph
        self.base_formula = base_formula
        self.protocol = protocol
        self.threshold = threshold
        self.end_time_point_var = self.graph.get_end_time_var(self.protocol)

    def minimize(self, supremum_duration, infimum_duration=0.0):
        """
        Recursive search for minimum duration of a protocol
        :param infimum_duration:
        :param supremum_duration:
        :return: minimum
        """
        if supremum_duration - infimum_duration > self.threshold:
            # Have not found a suitably minimal duration yet

            # Check whether there is a smaller duration below the midpoint
            mid_duration = (infimum_duration + supremum_duration) / 2.0
            left_duration = self.bounded_check(infimum_duration, mid_duration)

            if left_duration:
                # Found a smaller duration, update suprememum
                supremum_duration = left_duration
            else:
                # Did not find a smaller duration, so update infimum
                infimum_duration = mid_duration

            # Recurse on the half that has a possible minimum
            duration = self.minimize(supremum_duration, infimum_duration=infimum_duration)
        else:
            duration = supremum_duration

        return duration

    def bounded_check(self, infimum_duration, supremum_duration):
        """
        Encode constraints for infimum and supremum and check if feasible
        :param infimum_duration:
        :param supremum_duration:
        :return: duration if feasible or None
        """
        formula = pysmt.shortcuts.And([
            self.base_formula,
            pysmt.shortcuts.LT(self.end_time_point_var, pysmt.shortcuts.Real(supremum_duration)),
            pysmt.shortcuts.GE(self.end_time_point_var, pysmt.shortcuts.Real(infimum_duration)),
        ])
        result = pysmt.shortcuts.get_model(formula)
        duration = None
        if result:
            duration = self.graph.get_duration(result, self.protocol)

        return duration
