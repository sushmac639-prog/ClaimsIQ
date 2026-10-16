pipeline {
    agent any

    environment {
        IMAGE_NAME = 'claimiq-api'
        // Configure this credential in Jenkins as a username/password or registry credential.
        ACR_CREDENTIALS = credentials('claimiq-acr-credentials')
        ACR_LOGIN_SERVER = 'REPLACE_ACR_LOGIN_SERVER.azurecr.io'
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Python tests') {
            steps {
                sh 'python3 -m venv .venv-ci'
                sh '. .venv-ci/bin/activate && pip install -r requirements.txt'
                sh '. .venv-ci/bin/activate && python -m compileall -q app migrations scripts tests'
                sh '. .venv-ci/bin/activate && DATABASE_URL=sqlite:///./jenkins.db JWT_SECRET_KEY=ci-only-secret AI_PROVIDER=openai OPENAI_API_KEY=test-key pytest -q'
            }
        }

        stage('Docker build') {
            steps {
                sh 'docker build -t ${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${BUILD_NUMBER} .'
            }
        }

        stage('Docker push') {
            when { expression { return env.ACR_LOGIN_SERVER != 'REPLACE_ACR_LOGIN_SERVER.azurecr.io' } }
            steps {
                sh 'echo "$ACR_CREDENTIALS_PSW" | docker login ${ACR_LOGIN_SERVER} -u "$ACR_CREDENTIALS_USR" --password-stdin'
                sh 'docker push ${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${BUILD_NUMBER}'
            }
        }
    }

    post {
        always { sh 'rm -rf .venv-ci jenkins.db || true' }
    }
}
