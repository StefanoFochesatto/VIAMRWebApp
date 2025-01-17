# Use the specified base image from Docker Hub
FROM stefanofochesatto/viamr:latest

# Switch to root to install system dependencies
USER root

# Update apt-get repositories and install system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common && \
    add-apt-repository universe && \
    apt-get update && \
    apt-get install -y \
    libgl1 \
    libglx-mesa0 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*
# Ensure the installed libraries are accessible by all users
RUN chmod -R 755 /usr/lib/x86_64-linux-gnu

# Change the UID of the firedrake user to 1000
RUN usermod -u 1000 firedrake && \
    groupmod -g 1000 firedrake && \
    find / -user 1001 -exec chown -h 1000 {} \; || true

# Switch back to the firedrake user
USER firedrake
WORKDIR /home/firedrake

# Set useful environment variables
ENV LC_ALL=C.UTF-8
ENV PETSC_ARCH=default
ENV PETSC_DIR=/home/firedrake/petsc
ENV MPICH_DIR=${PETSC_DIR}/packages/bin
ENV HDF5_DIR=${PETSC_DIR}/packages
ENV HDF5_MPI=ON
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV PYVISTA_OFF_SCREEN=True
ENV PYVISTA_USE_XVFB=True

# Activate the Firedrake environment and install Python dependencies
RUN bash -c "source firedrake/bin/activate && \
    pip install streamlit stpyvista && \
    git clone https://github.com/viskex/viskex.git && \
    cd viskex && pip install '.[tutorials]' && \
    cd /home/firedrake"

# Clone the Streamlit application repository
RUN git clone https://github.com/StefanoFochesatto/VIAMRWebApp.git

# Expose the application port
EXPOSE 7860

CMD ["bash", "-c", "source firedrake/bin/activate && cd /home/firedrake/VIAMRWebApp && streamlit run streamlitapp.py --server.address 0.0.0.0 --server.port 7860"]
