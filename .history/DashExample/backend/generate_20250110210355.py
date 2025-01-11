from flask import Flask, request, jsonify
import pyvista as pv
import os

app = Flask(__name__)

DATA_DIR = "/app/shared_data"
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/generate_vtu", methods=["POST"])
def generate_vtu():
    data = request.get_json() or {}
    resolution = int(data.get("resolution", 20))

    # Create a PolyData sphere and cast to UnstructuredGrid
    mesh_poly = pv.Sphere(phi_resolution=resolution,
                          theta_resolution=resolution)
    mesh_ugrid = mesh_poly.cast_to_unstructured_grid()

    filename = "my_sphere.vtu"
    filepath = os.path.join(DATA_DIR, filename)
    mesh_ugrid.save(filepath)

    return jsonify({"status": "ok", "filename": filename})


if __name__ == "__main__":
    # Simple Flask server for local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
