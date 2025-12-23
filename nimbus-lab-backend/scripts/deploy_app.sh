set -e
set -o pipefail
export DEBIAN_FRONTEND=noninteractive

REPO_URL=$1
APP_NAME=$2
FRAMEWORK=$3
APP_PORT=$4

log() { echo "$1"; }

# Go to /opt folder
mkdir -p /opt/apps
cd /opt/apps

log "Cleaning up existing containers with the same name..."
docker stop $APP_NAME || true
docker rm $APP_NAME || true

log "Cloning repository..."
if [ -d "$APP_NAME" ]; then
    log "Removing existing repository folder..."
    rm -rf "$APP_NAME"
fi

git clone $REPO_URL $APP_NAME 2>&1 | tee /dev/stdout
cd $APP_NAME

# Create Dockerfile dynamically if not exists
if [ ! -f "Dockerfile" ]; then
    log "Generating dynamic Dockerfile for $FRAMEWORK..."
    case $FRAMEWORK in
      react|nodejs)
        # Check if it's a Vite project
        if grep -q "vite" package.json; then
            cat > Dockerfile <<EOF
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
RUN npm install -g serve
CMD ["serve", "-s", "dist", "-l", "$APP_PORT"]
EOF
        else
            cat > Dockerfile <<EOF
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "start"]
EOF
        fi
        ;;
      django)
        cat > Dockerfile <<EOF
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "projectname.wsgi", "--bind", "0.0.0.0:$APP_PORT"]
EOF
        ;;
      flask)
        cat > Dockerfile <<EOF
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$APP_PORT"]
EOF
        ;;
      *)
        log "Framework not supported"
        exit 1
        ;;
    esac
else
    log "Using existing Dockerfile found in repository."
fi

log "Building Docker image..."
docker build -t $APP_NAME . 2>&1 | tee /dev/stdout

log "Running container..."
docker run -d --name $APP_NAME --restart unless-stopped -p $APP_PORT:$APP_PORT $APP_NAME 2>&1 | tee /dev/stdout

log "App deployed successfully at port $APP_PORT!"
