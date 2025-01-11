FROM python:3.9-slim

# Set the working directory
WORKDIR /app
# Set environment variables for PyVista headless rendering
ENV PYVISTA_OFF_SCREEN=True
ENV PYVISTA_USE_XVFB=True

# Install necessary packages for PyVista headless rendering
RUN apt-get update && apt-get install -y \
    xvfb \
    libgl1-mesa-glx \
    libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY app.py requirements.txt /app/

# Install Python dependencies
RUN pip install -r requirements.txt


# Start Xvfb and then the Streamlit app
CMD ["bash", "-c", "streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]
