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
from collections import defaultdict

class PrefixSpan:
    def __init__(self, projection):
        self.projection = projection

    def frequent(self, min_occ):
        results = self._prefix_span([], self.projection, min_occ)
        results.sort(key=lambda x: x[1], reverse=True)
        inverted = [(supp, pattern) for pattern, supp in results]
        return inverted

    def _prefix_span(self, prefix, proj_db, min_occ):
        results = []
        freq_items = self._find_freq_items(proj_db, min_occ)
        for item, supp in sorted(freq_items.items()):  # Sort items for consistent order
            new_prefix = prefix + [item]
            results.append((new_prefix, supp))
            new_proj_db = self._project(proj_db, item)
            results.extend(self._prefix_span(new_prefix, new_proj_db, min_occ))
        return results

    def _find_freq_items(self, proj_db, min_occ):
        item_count = defaultdict(int)
        for seq in proj_db:
            seen = set()
            for item in seq:
                if item not in seen:
                    item_count[item] += 1
                    seen.add(item)
        return {item: count for item, count in item_count.items() if count >= min_occ}

    def _project(self, proj_db, item):
        new_db = []
        for seq in proj_db:
            found = False
            for i in range(len(seq)):
                if not found and seq[i] == item:
                    found = True
                    suffix = seq[i+1:]
                    if suffix:
                        new_db.append(suffix)
                    break
        return new_db
