param(
    [string]$InputPath = "d:\GitHub\digitalbook\book_29_export.json",
    [string]$OutputPath = "d:\GitHub\digitalbook\book_29_export.json"
)

if (-not (Test-Path $InputPath)) {
    Write-Error "Fichier introuvable: $InputPath"
    exit 1
}

try {
    $data = Get-Content -Raw -Path $InputPath | ConvertFrom-Json
} catch {
    Write-Error "Erreur de lecture/parse JSON: $($_.Exception.Message)"
    exit 1
}

$out = [ordered]@{ chapters = @() }

foreach ($ch in $data.chapters) {
    $newChapter = [ordered]@{
        title      = $ch.title
        content    = $ch.content
        order      = $ch.order
        thematique = $null
        sections   = @()
    }

    if ($ch.thematique) {
        $newChapter.thematique = [ordered]@{
            id          = $ch.thematique.id
            title       = $ch.thematique.title
            description = $ch.thematique.description
        }
    }

    foreach ($sec in $ch.sections) {
        $newSec = [ordered]@{
            title       = $sec.title
            content     = $sec.content
            order       = $sec.order
            images      = @()
            tables      = @()
            subsections = @()
        }

        if ($sec.images) { $newSec.images = @($sec.images) } else { $newSec.images = @() }
        if ($sec.tables) { $newSec.tables = @($sec.tables) } else { $newSec.tables = @() }

        foreach ($sub in $sec.subsections) {
            $newSub = [ordered]@{
                title   = $sub.title
                content = $sub.content
                order   = $sub.order
                images  = @()
                tables  = @()
            }

            if ($sub.images) { $newSub.images = @($sub.images) } else { $newSub.images = @() }
            if ($sub.tables) { $newSub.tables = @($sub.tables) } else { $newSub.tables = @() }

            $newSec.subsections += $newSub
        }

        $newChapter.sections += $newSec
    }

    $out.chapters += $newChapter
}

try {
    $json = $out | ConvertTo-Json -Depth 100
    Set-Content -Path $OutputPath -Value $json -Encoding UTF8
    Write-Host "Conversion terminée -> $OutputPath" -ForegroundColor Green
} catch {
    Write-Error "Erreur d'écriture JSON: $($_.Exception.Message)"
    exit 1
}
