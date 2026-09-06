param(
    [Parameter(Mandatory = $true)][string]$DocsRoot,
    [switch]$FailOnError
)

$ErrorActionPreference = "Continue"
$issues = 0

if (-not (Test-Path $DocsRoot)) {
    Write-Error "DocsRoot 不存在: $DocsRoot"
    exit 2
}

$files = Get-ChildItem $DocsRoot -Recurse -Filter "*.md" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\archive\\|\\node_modules\\|\\.git\\' }

foreach ($f in $files) {
    $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    $rel = $f.FullName.Substring((Resolve-Path $DocsRoot).Path.Length + 1)

    if ($content -notmatch '^---\s*\r?\n') {
        Write-Output "[MISSING-FRONTMATTER] $rel"
        $issues++
        continue
    }

    $fm = $content.Substring(0, $content.IndexOf("`n---", 4))
    foreach ($field in @('title', 'status')) {
        if ($fm -notmatch "(?m)^$field\s*:") {
            Write-Output "[MISSING-FIELD:$field] $rel"
            $issues++
        }
    }

    if ($fm -match "(?m)^status\s*:\s*(.+)$") {
        $status = $Matches[1].Trim()
        $valid = @('draft', 'approved', 'superseded', 'historical', 'archived')
        if ($status -notin $valid) {
            Write-Output "[INVALID-STATUS:$status] $rel"
            $issues++
        }
    }
}

if ($issues -gt 0) {
    Write-Output "发现 $issues 个问题"
    if ($FailOnError) { exit 1 }
} else {
    Write-Output "OK: 全部文档 front-matter 合法"
    exit 0
}