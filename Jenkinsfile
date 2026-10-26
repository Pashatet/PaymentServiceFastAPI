pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        DEPLOY_HOST = '172.31.41.81'
        REMOTE_DIR = '/opt/payment-service'
        IMAGE_NAME = 'payment-service'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Tests and lint') {
            steps {
                sh '''
                    docker run --rm \
                      -e PYTHONDONTWRITEBYTECODE=1 \
                      -v "$WORKSPACE:/workspace" \
                      -w /workspace \
                      python:3.12-slim \
                      sh -c 'python -m pip install --no-cache-dir -r requirements-dev.txt && ruff check --no-cache app tests && pytest -q -p no:cacheprovider'
                '''
            }
        }

        stage('Build Docker image') {
            steps {
                sh '''
                    docker build --pull \
                      --tag "$IMAGE_NAME:$BUILD_NUMBER" .
                '''
            }
        }

        stage('Deploy to App EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'app-server-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    sh '''
                        set -eu

                        docker save \
                          --output "payment-service-${BUILD_NUMBER}.tar" \
                          "$IMAGE_NAME:$BUILD_NUMBER"

                        scp -i "$SSH_KEY" \
                          -o BatchMode=yes \
                          -o StrictHostKeyChecking=yes \
                          docker-compose.yml \
                          "$SSH_USER@$DEPLOY_HOST:$REMOTE_DIR/docker-compose.yml"

                        scp -i "$SSH_KEY" \
                          -o BatchMode=yes \
                          -o StrictHostKeyChecking=yes \
                          "payment-service-${BUILD_NUMBER}.tar" \
                          "$SSH_USER@$DEPLOY_HOST:/tmp/payment-service-${BUILD_NUMBER}.tar"

                        ssh -i "$SSH_KEY" \
                          -o BatchMode=yes \
                          -o StrictHostKeyChecking=yes \
                          "$SSH_USER@$DEPLOY_HOST" \
                          "docker load -i /tmp/payment-service-${BUILD_NUMBER}.tar && rm -f /tmp/payment-service-${BUILD_NUMBER}.tar && cd '$REMOTE_DIR' && IMAGE_TAG='${BUILD_NUMBER}' docker compose up -d --remove-orphans && docker compose ps"

                        rm -f "payment-service-${BUILD_NUMBER}.tar"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'rm -f "payment-service-${BUILD_NUMBER}.tar"'
        }
    }
}