# Update all frontend files to use 127.0.0.1 instead of localhost
$files = Get-ChildItem -Path "frontend\src" -Recurse -Include *.tsx,*.ts

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    if ($content -match "localhost:8001") {
        $newContent = $content -replace "localhost:8001", "127.0.0.1:8001"
        Set-Content -Path $file.FullName -Value $newContent -NoNewline
        Write-Host "Updated: $($file.Name)"
    }
}

Write-Host "`nDone! Updated all files to use 127.0.0.1"
