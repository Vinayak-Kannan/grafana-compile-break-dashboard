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

        stage('HF Model Scan & Analysis') {
            steps {
                sh '''
                   . /opt/venv/bin/activate
                   cd scripts
                   python pull_hf_models.py 15
                '''
            }
        }

        stage('Generate Dynamo Explanations') {
            steps {
                sh '''
                    . /opt/venv/bin/activate
                    cd scripts
                    python dynamo_explain_creator.py
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
