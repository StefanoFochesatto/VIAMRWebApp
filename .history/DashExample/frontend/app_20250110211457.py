FROM python: 3.9-slim

WORKDIR / app

# Install system libs needed by PyVista + VTK
RUN apt-get update & & apt-get install - y \
    libgl1-mesa-glx \
    libxext6 \
    libxrender1 \
    libsm6 \
    libx11-6 \
    & & rm - rf / var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install - -no-cache-dir - r requirements.txt

COPY app.py .

EXPOSE 8050
CMD["python", "app.py"]
