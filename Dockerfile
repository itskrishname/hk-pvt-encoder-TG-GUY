# Base image
FROM artemisfowl004/vid-compress

WORKDIR /app

# Use Debian Buster archives (your current lines – keep them)
RUN echo "deb http://archive.debian.org/debian buster main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main contrib non-free" >> /etc/apt/sources.list && \
    apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
        git \
        python3 \
        python3-pip \
        fontconfig \
        wget \
        zstd \
        p7zip \
        xz-utils \
        curl \
        tar && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# CHANGE THIS LINE — USE THE "FULL" BUILD WITH drawtext, subtitles, fonts
RUN cd /tmp && \
    wget -q https://www.johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg && \
    mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf ffmpeg-* && \
    cd /app

# Keep fonts (DejaVu works great with drawtext)
RUN apt-get -qq update && apt-get -qq install -y \
    fonts-dejavu-core \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod -R 755 /app

CMD ["bash", "start.sh"]
