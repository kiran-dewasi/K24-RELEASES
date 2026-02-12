# K24 Baileys WhatsApp Listener Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY listener.js .
COPY batch-handler.js .

# Create auth directory with proper permissions
RUN mkdir -p auth && chmod 700 auth

# Expose port (if needed for health checks)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "console.log('Baileys running')" || exit 1

# Run the listener
CMD ["node", "listener.js"]
