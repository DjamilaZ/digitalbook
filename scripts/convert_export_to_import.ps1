param(
    [string]$InputPath = "d:\GitHub\digitalbook\book_29_export.json",
    [string]$OutputPath
)

if (-not (Test-Path $InputPath)) {
    Write-Error "Fichier introuvable: $InputPath"
    exit 1
}

try {
    $data = Get-Content -Raw -Encoding UTF8 -Path $InputPath | ConvertFrom-Json
} catch {
    Write-Error "Erreur de lecture/parse JSON: $($_.Exception.Message)"
    exit 1
}

# Définir un chemin de sortie par défaut si non fourni: <Input>_import.json
if (-not $PSBoundParameters.ContainsKey('OutputPath') -or [string]::IsNullOrWhiteSpace($OutputPath)) {
    $dir = Split-Path -Parent $InputPath
    $name = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)
    $OutputPath = Join-Path $dir ("{0}_import.json" -f $name)
}

# Construire la structure attendue par create_book_hierarchy_from_provided_json
$out = [ordered]@{
    titre_livre = $data.book.title
    thematiques = @()
}

# Regroupement par thématique et collecte des chapitres sans thématique
$thematiquesMap = @{}
$chaptersSansThematique = @()

foreach ($ch in $data.chapters) {
    # Créer le chapitre converti (sans id, sans qcm)
    $newChapter = [ordered]@{
        title    = $ch.title
        content  = $ch.content
        order    = $ch.order
        sections = @()
    }

    # Trier les sections par 'order' si présent
    $sections = @()
    if ($ch.sections) { $sections = @($ch.sections) }
    $sections = $sections | Sort-Object { if ($_.order -ne $null) { [int]$_.order } else { 0 } }

    foreach ($sec in $sections) {
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

        # Trier les sous-sections par 'order' si présent
        $subs = @()
        if ($sec.subsections) { $subs = @($sec.subsections) }
        $subs = $subs | Sort-Object { if ($_.order -ne $null) { [int]$_.order } else { 0 } }

        foreach ($sub in $subs) {
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

    if ($ch.thematique) {
        $tid = $ch.thematique.id
        if (-not $thematiquesMap.ContainsKey($tid)) {
            $thematiquesMap[$tid] = [ordered]@{
                title       = $ch.thematique.title
                description = $ch.thematique.description
                chapters    = @()
            }
        }
        $thematiquesMap[$tid].chapters += $newChapter
    } else {
        # Pour chapters_sans_thematique, utiliser l'ancienne nomenclature: 'titre'/'contenu'
        $oldChapter = [ordered]@{
            titre    = $newChapter.title
            contenu  = $newChapter.content
            order    = $newChapter.order
            sections = $newChapter.sections
        }
        $chaptersSansThematique += $oldChapter
    }
}

# Trier les chapitres à l'intérieur de chaque thématique par 'order'
foreach ($tid in $thematiquesMap.Keys) {
    $sortedChapters = $thematiquesMap[$tid].chapters | Sort-Object { if ($_.order -ne $null) { [int]$_.order } else { 0 } }
    $thematiquesMap[$tid].chapters = @($sortedChapters)
}

# Construire le tableau de thématiques (tri par titre pour stabilité)
$thematiquesArray = @()
foreach ($key in ($thematiquesMap.Keys | Sort-Object { $thematiquesMap[$_].title })) {
    $thematiquesArray += $thematiquesMap[$key]
}
$out.thematiques = $thematiquesArray

# Ajouter les chapitres sans thématique si présents (triés par 'order')
if ($chaptersSansThematique.Count -gt 0) {
    $out.chapters_sans_thematique = @($chaptersSansThematique | Sort-Object { if ($_.order -ne $null) { [int]$_.order } else { 0 } })
}

try {
    $json = $out | ConvertTo-Json -Depth 100
    Set-Content -Path $OutputPath -Value $json -Encoding UTF8
    Write-Host "Conversion terminée -> $OutputPath" -ForegroundColor Green
} catch {
    Write-Error "Erreur d'écriture JSON: $($_.Exception.Message)"
    exit 1
}
