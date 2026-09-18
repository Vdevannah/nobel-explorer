# 1. Start with Node.js
FROM node:22-alpine

# 2. Working directory inside the container
WORKDIR /app

# 3. Copy package files first
COPY frontend/package*.json ./

# 4. Install frontend dependencies
RUN npm ci

# 5. Copy the React application
COPY frontend ./

# 6. Vite development server port
EXPOSE 5173

# 7. Start Vite
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]