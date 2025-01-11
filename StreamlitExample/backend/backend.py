from firedrake.output import VTKFile
from firedrake import *
from viamr.utility import SphereObstacleProblem, SpiralObstacleProblem
from viamr import VIAMR
from flask import Flask, request, jsonify
import os
import glob
import logging

app = Flask(__name__)
STORAGE_PATH = "/app/storage"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_storage():
    """Clean the storage directory contents without removing the mount point"""
    logger.info(f"Cleaning storage directory: {STORAGE_PATH}")
    if os.path.exists(STORAGE_PATH):
        for item in os.listdir(STORAGE_PATH):
            item_path = os.path.join(STORAGE_PATH, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                    logger.info(f"Removed file: {item_path}")
                elif os.path.isdir(item_path):
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if os.path.isfile(subitem_path):
                            os.unlink(subitem_path)
                            logger.info(f"Removed file: {subitem_path}")
                    os.rmdir(item_path)
                    logger.info(f"Removed directory: {item_path}")
            except Exception as e:
                logger.error(f"Error while cleaning storage: {e}")


@app.route("/solve", methods=["POST"])
def solve_problem():
    try:
        logger.info("Starting new solve request")
        clean_storage()

        data = request.json
        logger.info(f"Received parameters: {data}")

        if not data:
            return jsonify({"error": "No input data provided"}), 400

        max_iterations = data.get("max_iterations", 1)
        problem_type = data.get("problem", "Sphere")
        initTriHeight = data.get("initTriHeight", 0.3)
        RefinementMethod = data.get("RefinementMethod", "VCES")

        # Initialize problem
        if problem_type == "Sphere":
            problem_instance = SphereObstacleProblem(TriHeight=initTriHeight)
        else:
            problem_instance = SpiralObstacleProblem(TriHeight=initTriHeight)

        mesh_history = [problem_instance.setInitialMesh()]
        amr_instance = VIAMR()
        solutions = []
        u = None

        for i in range(max_iterations):
            logger.info(f"Processing iteration {i+1}/{max_iterations}")
            mesh = mesh_history[i]
            u, lb = problem_instance.solveProblem(mesh=mesh, u=u)
            u.rename("solution")

            if RefinementMethod == "UDO":
                mark = amr_instance.udomark(
                    mesh, u, lb, n=data.get("neighbors", 3))
            else:  # VCES
                bracket = data.get("bracket", [0.2, 0.8])
                mark = amr_instance.vcesmark(mesh, u, lb, bracket)

            solutions.append(u)
            mesh = mesh.refine_marked_elements(mark)
            mesh_history.append(mesh)

            output_file = os.path.join(STORAGE_PATH, f"solution_{i}.pvd")
            VTKFile(output_file).write(u)
            logger.info(f"Wrote solution file: {output_file}")

        # Get only .pvd files
        pvd_files = glob.glob(os.path.join(STORAGE_PATH, "*.pvd"))
        pvd_files = [os.path.basename(f) for f in pvd_files]

        logger.info(f"Generated files: {pvd_files}")
        return jsonify({
            "message": "Solutions generated successfully",
            "files": sorted(pvd_files)
        })

    except Exception as e:
        logger.error(f"Error during computation: {str(e)}", exc_info=True)
        return jsonify({
            "error": "An error occurred during computation",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    logger.info("Starting Flask application")
    clean_storage()
    app.run(host="0.0.0.0", port=5000)
