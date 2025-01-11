from flask import Flask, request, jsonify, send_file
import os
import pyvista as pv  # Example usage if you want to generate .vtu
# You can also use the 'VTK' library directly, etc.

app = Flask(__name__)

# Directory where we store the generated .vtu files
DATA_DIR = "/app/data_output"
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/generate_vtu", methods=["POST"])
def generate_vtu():
    """
    Endpoint that receives user parameters via JSON,
    generates a .vtu file, and returns the filename to the frontend.
    """
    params = request.get_json() or {}
    # e.g., params might contain resolution, shape type, etc.
    resolution = int(params.get("resolution", 20))

    # TODO: Implement your real mesh logic here.
    # For now, let's just create a placeholder PyVista mesh:
    mesh = pv.Sphere(phi_resolution=resolution, theta_resolution=resolution)

    # Name your output file
    filename = "my_sphere.vtu"
    filepath = os.path.join(DATA_DIR, filename)

    # Save as .vtu
    mesh.save(filepath)

    # Return the filename so the frontend can fetch it
    return jsonify({"status": "ok", "filename": filename})


@app.route("/data/<filename>", methods=["GET"])
def serve_file(filename):
    """
    Serve the generated .vtu file so Dash VTK can load it.
    """
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.isfile(filepath):
        # Directly return file
        return send_file(filepath, as_attachment=False)
    else:
        return jsonify({"error": f"File {filename} not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
