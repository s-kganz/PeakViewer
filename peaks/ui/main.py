# -- Set config options --
from kivy import Config
Config.set('graphics', 'minimum_width', '300')
Config.set('graphics', 'minimum_height', '500')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# -- Core kivy modules --
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from kivy.uix.treeview import TreeViewNode, TreeViewLabel
from kivy_garden.graph import MeshLinePlot, Graph

# -- Other python modules --
import numpy as np

# -- Namespace modules --

class MyLayout(FloatLayout):
    '''
    Custom layout built off of a stack layout.
    '''
    tree = ObjectProperty(None)
    graph = ObjectProperty(None)
    status_bar = ObjectProperty(None)
    meshes = []

    def create_random_plot(self):
        plot = MeshLinePlot(color=[1, 0, 0, 1])
        x = np.linspace(1, 100, num=100)
        y = np.sin(x) * 2 + np.random.normal(0, 1, len(x))
        plot.points = [(a,b) for (a,b) in zip(x, y)]
        self.meshes.append(plot)

        self.graph.add_plot(plot)

    def clear_all_plots(self):
        for mesh in self.meshes:
            self.graph.remove_plot(mesh)
        
        self.meshes.clear()

class PySpecApp(App):
    def build(self):
        layout = MyLayout()
        return layout

if __name__ == '__main__':
    PySpecApp().run()