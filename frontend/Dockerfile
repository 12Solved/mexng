FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_BASE_PATH=/
RUN VITE_BASE_PATH=$VITE_BASE_PATH npx vite build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/nginx.conf.template
ARG VITE_BASE_PATH=/
ENV BASE_PATH=$VITE_BASE_PATH
CMD ["/bin/sh", "-c", "envsubst '${BASE_PATH}' < /etc/nginx/conf.d/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
EXPOSE 80
