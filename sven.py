import urwid

import urwid

def MaxWidth(w, max_width, align="center"):
    # align: "left", "center", "right"
    if align == "left":
        return urwid.Columns([("fixed", max_width, w), urwid.Text("")])
    elif align == "right":
        return urwid.Columns([urwid.Text(""), ("fixed", max_width, w)])
    else:  # center
        return urwid.Columns([
            urwid.Text(""),
            ("fixed", max_width, w),
            urwid.Text(""),
        ])

def MaxHeight(w, max_height, valign="middle"):
    # valign: "top", "middle", "bottom"
    limited = urwid.BoxAdapter(w, height=max_height)
    filler = urwid.Filler(limited, valign=valign)
    return filler


def BoundedContainer(widget, max_width=None, max_height=None,
                     align="center", valign="middle"):

    w = widget
    if max_width is not None:
        w = MaxWidth(w, max_width, align)

    if max_height is not None:
        # BoxAdapter expects a box widget.
        # If 'w' is a flow widget (Text, Edit), wrap it first:
        if isinstance(w, urwid.Text) or isinstance(w, urwid.Edit):
            w = urwid.Filler(w, valign="top")
        w = MaxHeight(w, max_height, valign)

    return w