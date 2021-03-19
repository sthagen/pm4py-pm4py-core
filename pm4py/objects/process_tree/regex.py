from pm4py.objects.process_tree import process_tree as pt_operator
from pm4py.util.regex import SharedObj, get_new_char


def pt_to_regex(tree, rec_depth=0, shared_obj=None, parameters=None):
    """
    Transforms a process tree to a regular expression

    NB: The conversion is not yet working with trees containing an AND and/or an OR operator!

    Parameters
    ------------
    tree
        Process tree
    parameters
        Possible parameters of the algorithm
    """
    if parameters is None:
        parameters = {}

    if shared_obj is None:
        shared_obj = SharedObj()

    stru = ""

    if tree.operator is not None:
        contains_tau = len(list(child for child in tree.children if child.operator is None and child.label is None)) > 0
        children_rep = []
        for child in tree.children:
            rep, shared_obj = pt_to_regex(child, rec_depth=rec_depth + 1, shared_obj=shared_obj, parameters=parameters)
            children_rep.append(rep)
        if tree.operator == pt_operator.Operator.SEQUENCE:
            children_rep = [x for x in children_rep if not x is None]
            stru = "(" + "".join(children_rep) + ")"
        elif tree.operator == pt_operator.Operator.XOR:
            children_rep = [x for x in children_rep if not x is None]
            stru = "(" + "|".join(children_rep) + ")"
            if contains_tau:
                stru = "(" + stru + "?)"
        elif tree.operator == pt_operator.Operator.LOOP:
            children_rep = [x for x in children_rep if not x is None]
            if len(children_rep) == 1:
                stru = "(" + children_rep[0] + ")+"
            else:
                stru = "(" + "".join(children_rep) + ")*" + children_rep[0]
        elif tree.operator == pt_operator.Operator.PARALLEL:
            raise Exception("the conversion is not yet working with trees containing an AND and/or an OR operator!")
        elif tree.operator == pt_operator.Operator.OR:
            raise Exception("the conversion is not yet working with trees containing an AND and/or an OR operator!")

    elif tree.label is not None:
        if tree.label not in shared_obj.mapping_dictio:
            get_new_char(tree.label, shared_obj)
        stru = shared_obj.mapping_dictio[tree.label]
    elif tree.label is None:
        return None, shared_obj

    if rec_depth == 0:
        ret = "^" + stru + "$", shared_obj.mapping_dictio
        # print(ret)
        return ret

    return stru, shared_obj
