FROM stefanofochesatto/viamr:latest

# Set the working directory to the same directory used in the base image
USER firedrake
WORKDIR /home/firedrake

# Copy the application code and requirements
COPY backend.py requirements.txt /app/

# Activate the environment and install additional dependencies
RUN bash -c "source firedrake/bin/activate && pip install -r /app/requirements.txt"

# Run the backend application within the activated environment
CMD ["bash", "-c", "source firedrake/bin/activate && python /app/backend.py"]
