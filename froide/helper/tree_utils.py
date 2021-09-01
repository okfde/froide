from treebeard.mp_tree import MP_Node


def _inc_path(path):
    """:returns: The path of the next sibling of a given node path."""
    newpos = MP_Node._str2int(path[-MP_Node.steplen :]) + 1
    key = MP_Node._int2str(newpos)
    if len(key) > MP_Node.steplen:
        raise Exception("Path Overflow from")
    return "{0}{1}{2}".format(
        path[: -MP_Node.steplen],
        MP_Node.alphabet[0] * (MP_Node.steplen - len(key)),
        key,
    )


def get_new_child_params(leaf, last_child=False):
    if leaf is None:
        return {"depth": 1, "path": MP_Node._get_path(None, 1, 1)}
    if last_child is False:
        last_child = leaf.get_last_child()
    depth = leaf.depth + 1
    if last_child is None:
        path = MP_Node._get_path(leaf.path, depth, 1)
    else:
        path = _inc_path(last_child.path)

    return {"depth": depth, "path": path}


def add_children(leaf, get_children):
    children = get_children(leaf)
    leaf.numchild += len(children)
    leaf.save()
    last_child = leaf.get_last_child()
    for child in children:
        params = get_new_child_params(leaf, last_child=last_child)
        child.depth = params["depth"]
        child.path = params["path"]
        child.save(update_fields=["path", "depth"])
        last_child = child
        add_children(child, get_children)
