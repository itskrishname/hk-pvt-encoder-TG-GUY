# Base image
FROM artemisfowl004/vid-compress

WORKDIR /app

RUN echo "deb http://archive.debian.org/debian buster main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main contrib non-free" >> /etc/apt/sources.list && \
    apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
        git \
        python3 \
        python3-pip \
        fontconfig \
        wget \
        curl \
        tar \
        xz-utils \
        p7zip-full && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install FULL FFmpeg from BtbN (includes drawtext)
RUN cd /tmp && \
    wget -q https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz && \
    tar -xf ffmpeg-master-latest-linux64-gpl.tar.xz && \
    mv ffmpeg-master-latest-linux64-gpl/bin/* /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf ffmpeg-master-latest-linux64-gpl*

# Fonts for drawtext (DejaVu via apt — simple)
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    fonts-dejavu-core \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod -R 755 /app

CMD ["bash", "start.sh"]
