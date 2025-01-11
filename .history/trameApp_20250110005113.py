from __future__ import annotations
import numpy as np
import pyvista as pv
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame_vuetify.ui.vuetify3 import SinglePageLayout

pv.OFF_SCREEN = True

server = get_server(client_type="vue3")
state, ctrl = server.state, server.controller

# Make some random points. Seed the rng for reproducibility.
rng = np.random.default_rng(seed=0)
poly = pv.PolyData(rng.random((10, 3)))
poly["My Labels"] = [f"Label {i}" for i in range(poly.n_points)]
plotter = pv.Plotter()
plotter.add_point_labels(poly, "My Labels", point_size=20, font_size=36)

with SinglePageLayout(server) as layout:
    with layout.content as body:
        view = plotter_ui(plotter, mode='client')
        ctrl.view_update = view.update
        ctrl.view_update_image = view.update_image
        ctrl.reset_camera = view.reset_camera

if __name__ == "__main__":
    server.start()
