import math
from typing import List
import operator

class Interval:
    @staticmethod
    def intersect(intervals: List[List[float]]) -> List[float]:
        """
        Compute the intersection of intervals appearing in the intervals list
        :param intervals: The set of intervals to intersect
        :return: interval
        """
        result = None
        for i in intervals:
            if not result:
                result = i
            else:
                result[0] = i[0] if result[0] <= i[0] and i[0] <= result[1] else result[0]
                result[1] = i[1] if result[0] <= i[1] and i[1] <= result[1] else result[1]
        return result

    @staticmethod
    def substitute_infinity(infinity: float, interval_list: List[List[float]]) -> List[List[float]]:
        for interval in interval_list:
            interval[0] = infinity if interval[0] == math.inf else interval[0]
            interval[1] = infinity if interval[1] == math.inf else interval[1]
        return interval_list
      

# junk code to print out the results in a slightly easier to read output
def print_debug(result, graph):
    def make_entry(variable, activity, uri, value, prefix = ""):
        v = value
        if activity.start.identity == variable.identity:
            s = f"{prefix}S {activity.identity} : {value}"
        elif activity.end.identity == variable.identity:
            s = f"{prefix}E {activity.identity} : {value}"
        elif activity.duration.identity == variable.identity:
            s = f"{prefix}D {uri} : {value}"
        else:
            s = f"{prefix}ERR {uri} : {value}"
        return (v, s)
    nodes = []
    protcols = []
    for (node, value) in result:
        uri = node.symbol_name()
        v = (float)(value.constant_value())
        if uri in graph.nodes:
            variable = graph.nodes[uri]
            activity = variable.get_parent()
            nodes.append(make_entry(variable, activity, uri, v))
        else:
            variable = graph.doc.find(uri)
            activity = variable.get_parent()
            protcols.append(make_entry(variable, activity, uri, v, "PROTOCOL "))

    print("--- Nodes ---")
    for k in sorted(nodes, key=operator.itemgetter(0)):
        print(k[1])
    print("--- Protocol ---")
    for k in sorted(protcols, key=operator.itemgetter(0)):
        print(k[1])