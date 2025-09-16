param(
    [string]$JsonPath = "d:\GitHub\digitalbook\livre_digital_structured_v2.json",
    [string]$Title = "LIVRET DIGITAL LEVAGE",
    [switch]$Replace
)

Write-Host "==> Vérification du JSON..." -ForegroundColor Cyan
if (-not (Test-Path $JsonPath)) {
    Write-Error "Fichier JSON introuvable: $JsonPath"
    exit 1
}

# S'assure que le JSON est visible dans le conteneur backend (montage ./digitalbook -> /app)
$dest = "d:\GitHub\digitalbook\digitalbook\" + [IO.Path]::GetFileName($JsonPath)
if ($JsonPath -ne $dest) {
    Write-Host "==> Copie du JSON dans digitalbook/ pour le conteneur..." -ForegroundColor Cyan
    Copy-Item -Path $JsonPath -Destination $dest -Force
}

Write-Host "==> Démarrage des services Docker (db, backend)..." -ForegroundColor Cyan
& docker compose up -d db backend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Application des migrations Django..." -ForegroundColor Cyan
& docker compose exec backend python manage.py migrate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Chemin interne au conteneur
$containerJson = "/app/" + [IO.Path]::GetFileName($dest)

# Construction de la commande d'import
$cmd = @(
    "python",
    "manage.py",
    "import_book",
    "--json-path", $containerJson,
    "--title", $Title
)
if ($Replace) { $cmd += "--replace" }

Write-Host "==> Import du livre dans la base..." -ForegroundColor Cyan
& docker compose exec backend @cmd
exit $LASTEXITCODE
