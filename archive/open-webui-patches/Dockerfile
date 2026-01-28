# Open WebUI with MCP Group Header Forwarding
# Extends official image and patches for multi-tenant support

FROM ghcr.io/open-webui/open-webui:v0.7.2

# Copy patch files
COPY headers.py /app/patches/headers.py
COPY apply-patches.sh /app/patches/apply-patches.sh

# Make patch script executable
RUN chmod +x /app/patches/apply-patches.sh

# Use patch script as entrypoint wrapper
ENTRYPOINT ["/app/patches/apply-patches.sh"]
CMD ["bash", "start.sh"]
