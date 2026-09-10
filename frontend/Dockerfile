# Frontend Dockerfile
FROM node:20

WORKDIR /app

# Copy package files first (cache npm install)
COPY package*.json ./
RUN npm install

# Copy the frontend code
COPY . .

EXPOSE 5173

# Serve frontend
CMD ["npm", "run", "dev", "--", "--host"]

