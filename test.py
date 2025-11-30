import urwid

def show_or_exit(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()

big = urwid.BigText(('banner', "Hello world"), urwid.HalfBlock5x4Font())
# wrap with Padding so it behaves as a flow widget (ListBox / top-widget friendly)
widget = urwid.Padding(big, width='clip')
fill = urwid.Filler(widget, 'middle')  # center vertically

loop = urwid.MainLoop(fill, palette=[('banner', 'light gray', 'dark blue')], unhandled_input=show_or_exit)
loop.run()
