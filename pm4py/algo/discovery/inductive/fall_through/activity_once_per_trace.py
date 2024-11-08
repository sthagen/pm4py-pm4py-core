'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

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
import copy
from typing import Any, Optional, Dict

from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from pm4py.algo.discovery.inductive.fall_through.activity_concurrent import ActivityConcurrentUVCL
from pm4py.util.compression import util as comut


class ActivityOncePerTraceUVCL(ActivityConcurrentUVCL):

    @classmethod
    def _get_candidate(cls, obj: IMDataStructureUVCL, pool=None, manager=None, parameters: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        candidates = sorted(list(comut.get_alphabet(obj.data_structure)))
        for t in obj.data_structure:
            cc = [x for x in candidates]
            for candi in cc:
                if len(list(filter(lambda e: e == candi, t))) != 1:
                    candidates.remove(candi)
            if len(candidates) == 0:
                return None
        return next(iter(candidates))
