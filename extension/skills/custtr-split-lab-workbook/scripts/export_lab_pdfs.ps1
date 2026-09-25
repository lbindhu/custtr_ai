param(
    [Parameter(Mandatory = $true)]
    [string]$Folder
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Folder)) {
    Write-Error "Folder not found: $Folder"
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false

try {
    Get-ChildItem -LiteralPath $Folder -Filter "0*.docx" |
        Sort-Object Name |
        ForEach-Object {
            $pdf = [System.IO.Path]::ChangeExtension($_.FullName, ".pdf")
            if (Test-Path -LiteralPath $pdf) {
                Remove-Item -LiteralPath $pdf -Force
            }
            $doc = $word.Documents.Open($_.FullName, $false, $true)
            $doc.ExportAsFixedFormat($pdf, 17)
            $doc.Close($false)
            Write-Output "Exported: $([System.IO.Path]::GetFileName($pdf))"
        }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
