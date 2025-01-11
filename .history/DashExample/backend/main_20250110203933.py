from flask import Flask, request, jsonify, send_file
import os
import pyvista as pv

app = Flask(__name__)

# Directory where we store or generate .vtu files
DATA_DIR = "/app/data_output"
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/generate_vtu", methods=["POST"])
def generate_vtu():
    """
    1) Read parameters (e.g., 'resolution') from JSON payload.
    2) Generate a PyVista mesh (Sphere), which is PolyData by default.
    3) Cast it to UnstructuredGrid so we can save as .vtu.
    4) Save to /app/data_output/my_sphere.vtu.
    5) Return a JSON response with the filename.
    """
    data = request.get_json() or {}
    resolution = int(data.get("resolution", 20))

    # Create a PolyData sphere
    mesh_polydata = pv.Sphere(
        phi_resolution=resolution, theta_resolution=resolution)

    # Cast to UnstructuredGrid to enable saving as .vtu
    mesh_ugrid = mesh_polydata.cast_to_unstructured_grid()

    filename = "my_sphere.vtu"
    filepath = os.path.join(DATA_DIR, filename)
    mesh_ugrid.save(filepath)

    return jsonify({"status": "ok", "filename": filename})


@app.route("/data/<path:filename>", methods=["GET"])
def serve_file(filename):
    """
    Serve the requested .vtu file (or any file) from DATA_DIR at /data/<filename>.
    Example: /data/my_sphere.vtu
    """
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.isfile(filepath):
        return send_file(filepath, as_attachment=False)
    return jsonify({"error": f"File '{filename}' not found"}), 404


if __name__ == "__main__":
    # For local debugging. In production, you'd typically use gunicorn, etc.
    app.run(host="0.0.0.0", port=5000, debug=True)
