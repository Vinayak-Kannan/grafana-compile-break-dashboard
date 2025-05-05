pipeline {
    agent any
    
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
                python scripts/collect_compile_breaks.py
                '''
            }
        }

        stage('Archive artifacts') {
            steps {
                archiveArtifacts artifacts: 'scripts/metrics/**',
                fingerprint: true
            }
        }
    }
}
