pipeline {
    agent any

    environment {
        PUSHGATEWAY_URL = 'http://pushgateway:9091'
    }
    
    stages {
        stage('Download Requirements') {
            steps {
                sh '''
                    . /opt/venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Collect compile-breaks') {
            steps {
                sh '''
                . /opt/venv/bin/activate
                python collect_compile_breaks.py
                '''
            }
        }

        stage('Archive artifacts') {
            steps {
                archiveArtifacts artifacts: 'metrics/**',
                fingerprint: true
            }
        }
    }
}
