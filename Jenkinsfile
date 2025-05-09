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
                    set -e

                    # for each category (Audio, Computer Vision, …)
                    for catdir in /inputs/*/; do
                        category="$(basename "$catdir")"
                        # for each .pkl in that category
                        for inp in "$catdir"/*.pkl; do
                        base="$(basename "$inp" .pkl)"
                        outdir="/dynamo_explain_output/$category"
                        outpkl="$outdir/${base}_dynamo_explain.pkl"

                        mkdir -p "$outdir"
                        echo "Running dynamo explain for $category/$base"

                        python dynamo_explain_creator.py \
                            --input-pkl "$inp" \
                            --output-pkl "$outpkl"
                        done
                    done
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
