from flask import Flask, request, jsonify, send_file
import os
import pyvista as pv

app = Flask(__name__)

# Directory to store .vtu files
DATA_DIR = "/app/data_output"
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/generate_vtu", methods=["POST"])
def generate_vtu():
    """
    Receive parameters (e.g., resolution) from the frontend,
    generate a PyVista mesh, cast to UnstructuredGrid, and save as .vtu.
    Return a JSON response with the filename.
    """
    data = request.get_json() or {}
    resolution = int(data.get("resolution", 20))

    # Example: Create a PolyData sphere
    mesh_polydata = pv.Sphere(
        phi_resolution=resolution, theta_resolution=resolution)

    # Cast PolyData -> UnstructuredGrid, so we can save to .vtu
    mesh_ugrid = mesh_polydata.cast_to_unstructured_grid()

    # Save as .vtu
    filename = "my_sphere.vtu"
    filepath = os.path.join(DATA_DIR, filename)
    mesh_ugrid.save(filepath)

    return jsonify({"status": "ok", "filename": filename})


@app.route("/data/<filename>", methods=["GET"])
def serve_file(filename):
    """
    Serve the saved .vtu file so the frontend can load it with dash_vtk.
    """
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.isfile(filepath):
        return send_file(filepath, as_attachment=False)
    return jsonify({"error": f"File '{filename}' not found"}), 404


if __name__ == "__main__":
    # For local debugging. In production, you might use gunicorn, etc.
    app.run(host="0.0.0.0", port=5000, debug=True)
