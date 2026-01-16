FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    xz-utils \
    tar \
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates \
    libass9 \
    libfreetype6 \
    libfontconfig1 \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxfixes3 \
    libopus0 \
    && rm -rf /var/lib/apt/lists/*

# Install STATIC FFmpeg (no dependencies needed)
RUN cd /tmp && \
    wget -q https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz && \
    tar -xf ffmpeg-master-latest-linux64-gpl.tar.xz && \
    mv ffmpeg-master-latest-linux64-gpl/bin/* /usr/local/bin/ && \
    rm -rf /tmp/*

# Check ffmpeg
RUN ffmpeg -version

WORKDIR /app
COPY . /app

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["bash", "start.sh"]
