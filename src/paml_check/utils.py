import math
from typing import List

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