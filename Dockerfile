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
        zstd \
        p7zip \
        xz-utils \
        curl \
        tar \
        ffmpeg \
        libavcodec-extra \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN fc-cache -fv

COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod -R 755 /app

CMD ["bash", "start.sh"]
