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

    # 1) Create a PyVista sphere as PolyData
    sphere_poly = pv.Sphere(phi_resolution=resolution,
                            theta_resolution=resolution)
    # 2) Cast PolyData -> UnstructuredGrid so we can save a .vtu
    sphere_ugrid = sphere_poly.cast_to_unstructured_grid()

    filename = "my_sphere.vtu"
    filepath = os.path.join(DATA_DIR, filename)

    # 3) Save to .vtu
    sphere_ugrid.save(filepath)

    print(f"Generated {filepath} with resolution={resolution}")
    return jsonify({"status": "ok", "filename": filename})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
