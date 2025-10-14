FROM ubuntu:plucky

# Install desktop environment, VNC server, and agent dependencies
RUN apt-get update && apt-get install -y \
    xfce4 xfce4-goodies \
    tightvncserver \
    dbus-x11 \
    firefox \
    python3 python3-pip python3-venv \
    xdotool wmctrl \
    scrot \
    curl \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome and wget
RUN apt-get update && apt-get install -y \
    python3-tk python3-dev \
    python3-xlib \
    wget \
    nano \
    gnupg \
    sudo \
    imagemagick \
    && wget -q -O /tmp/google-chrome-key.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg /tmp/google-chrome-key.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/google-chrome-key.gpg

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set up VNC user and password
RUN useradd -m dockeruser && echo "dockeruser:password" | chpasswd \
    && usermod -aG sudo dockeruser \
    && echo "dockeruser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Install uv for dockeruser
USER dockeruser
WORKDIR /home/dockeruser
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/dockeruser/.local/bin:${PATH}"

# Create .vnc directory for dockeruser
RUN mkdir -p /home/dockeruser/.vnc

# Copy VNC startup script and entrypoint
USER root
COPY xstartup /home/dockeruser/.vnc/xstartup
COPY entrypoint.sh /home/dockeruser/entrypoint.sh
RUN chown dockeruser:dockeruser /home/dockeruser/.vnc/xstartup /home/dockeruser/entrypoint.sh && \
    chmod +x /home/dockeruser/.vnc/xstartup /home/dockeruser/entrypoint.sh

# Copy agent code
COPY --chown=dockeruser:dockeruser . /home/dockeruser/kyros/
WORKDIR /home/dockeruser/kyros

# Install Python dependencies
USER dockeruser
RUN uv sync

# Install Playwright browsers (chromium and firefox)
RUN uv run playwright install chromium firefox
RUN uv run playwright install-deps chromium firefox

# Make run_agent.sh executable
RUN chmod +x /home/dockeruser/kyros/run_agent.sh

USER dockeruser
WORKDIR /home/dockeruser

# Expose VNC port
EXPOSE 5901

# Start VNC server on container startup
ENTRYPOINT ["/home/dockeruser/entrypoint.sh"]
