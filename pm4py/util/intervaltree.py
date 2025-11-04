'''
    PM4Py â€“ A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschrÃ¤nkt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
'''
class Interval:
    def __init__(self, start, end, data=None):
        if start >= end:
            raise ValueError("Start must be less than end")
        self.start = start
        self.end = end
        self.data = data or {}

    def overlaps(self, qstart, qend):
        return self.start < qend and self.end > qstart

    def contains(self, point):
        return self.start <= point <= self.end

    def __repr__(self):
        return f"Interval({self.start}, {self.end}, data={self.data})"

class IntervalTree:
    class Node:
        def __init__(self, interval):
            self.interval = interval
            self.max_end = interval.end
            self.left = None
            self.right = None

    def __init__(self):
        self.root = None

    def add(self, interval):
        if self.root is None:
            self.root = self.Node(interval)
            return

        stack = []
        curr = self.root
        while curr:
            stack.append(curr)
            if interval.start < curr.interval.start:
                if curr.left is None:
                    curr.left = self.Node(interval)
                    break
                curr = curr.left
            else:
                if curr.right is None:
                    curr.right = self.Node(interval)
                    break
                curr = curr.right

        # Update max_end from the parent up to the root
        while stack:
            curr = stack.pop()
            curr.max_end = curr.interval.end
            if curr.left:
                curr.max_end = max(curr.max_end, curr.left.max_end)
            if curr.right:
                curr.max_end = max(curr.max_end, curr.right.max_end)

    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.step is not None:
                raise ValueError("Step in slicing is not supported")
            qstart, qend = key.start, key.stop
            if qstart >= qend:
                return []
            return self._query_interval(self.root, qstart, qend)
        elif isinstance(key, (int, float)):
            return self._query_point(self.root, key)
        else:
            raise ValueError("Only slicing or point queries are supported")

    def _query_interval(self, node, qstart, qend):
        if node is None:
            return []

        result = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.interval.overlaps(qstart, qend):
                result.append(current.interval)
            if current.right and current.interval.start < qend:
                stack.append(current.right)
            if current.left and current.left.max_end >= qstart:
                stack.append(current.left)
        return result

    def _query_point(self, node, point):
        if node is None:
            return []

        result = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.interval.contains(point):
                result.append(current.interval)
            if current.right and current.interval.start <= point:
                stack.append(current.right)
            if current.left and current.left.max_end >= point:
                stack.append(current.left)
        return result
