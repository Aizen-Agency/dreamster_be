import os
from app import app
from app.services.deploy_contracts import DeployContracts

if __name__ == "__main__":
    # Deploy contracts on startup
    deploy_contracts = DeployContracts()
    compiled_contracts = deploy_contracts.compile_contracts()
    
    # Start the Flask server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)