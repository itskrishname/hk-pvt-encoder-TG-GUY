#base image
FROM artemisfowl004/vid-compress
RUN mkdir ./app
RUN chmod 777 /app
WORKDIR /app
RUN pip3 install --upgrade pip
RUN apt -qq update --fix-missing
RUN apt -qq install -y git \
    python3 \
    python3-pip \
    wget \
    zstd \
    p7zip \
    ffmpeg \
    curl
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
CMD ["bash","start.sh"]
