Write-Host "Starting Vespa and Ollama..."
docker compose up -d vespa ollama

Write-Host "Waiting for container initialization..."
Start-Sleep -Seconds 10

Write-Host "Deploying VespaSearch application..."
python .\scripts\deploy_vespa.py

Write-Host "Pulling Qwen 3 4B..."
docker compose exec ollama ollama pull qwen3:4b

Write-Host "Ready."
Write-Host "Vespa:  http://localhost:8080"
Write-Host "Ollama: http://localhost:11434"
