import gi
gi.require_version("Gtk","3.0")
from gi.repository import Gtk
v=Gtk.Window(title="Casillas Cerebro Prueba")
v.set_default_size(350,220)
c=Gtk.CheckButton(label="Mostrar cuadrícula")
v.add(c)
v.connect("destroy",Gtk.main_quit)
v.show_all()
c.grab_focus()
Gtk.main()
