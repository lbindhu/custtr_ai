---
name: custtr-vo-change
description: "Swaps the narrator voice in Articulate Storyline files via ElevenLabs."
  Also triggers when the user provides a .story file path and mentions ElevenLabs,
  a voice name, or asks to convert or update the narration.
  Always ask for the ElevenLabs API key at the start — never reuse one from memory.
---

# SL Voice Change

Replaces all embedded MP3 narration in Articulate Storyline `.story` files with a new
ElevenLabs voice using Speech-to-Speech (STS) conversion.

Supports **single-file** and **batch (folder)** modes.

---

## Step 0 — Collect inputs

Ask the user for:

1. **Input** — a single `.story` file path, or a folder of `.story` files
2. **Output path** — where to save the converted file(s)
3. **ElevenLabs API key** — ask every time; never pull from memory or prior sessions
4. **Target voice** — user may supply either:
   - A **Voice ID** directly (e.g. `TZl0VZDEkMLBwlPLAKD9`) — use as-is, skip lookup
   - A **voice name** (e.g. "Austin") — look it up via the API (Step 2)

---

## Step 1 — Prepare temp directories

Use `$env:TEMP` (the user's own temp folder, e.g. `C:\Users\<name>\AppData\Local\Temp`)
rather than `C:\Windows\Temp`. The system temp folder often denies cleanup access.

**Always wipe and recreate** per-file temp dirs at the start of each file — this prevents
leftover MP3s from a previous session from being picked up and re-converted.

```powershell
$tempBase  = $env:TEMP
$extractDir = Join-Path $tempBase "sl_vc_${fileIndex}_extracted"
$convertDir = Join-Path $tempBase "sl_vc_${fileIndex}_converted"
$roboCopyTmp = Join-Path $tempBase "sl_vc_robocopy_$fileIndex"

# Always start clean
Remove-Item $extractDir  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $convertDir  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $roboCopyTmp -Recurse -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path $extractDir  -Force | Out-Null
New-Item -ItemType Directory -Path $convertDir  -Force | Out-Null
New-Item -ItemType Directory -Path $roboCopyTmp -Force | Out-Null
```

---

## Step 2 — Resolve the voice ID

If the user gave a Voice ID directly, skip this step.

Otherwise, query the ElevenLabs API and find by name:

```powershell
$response = Invoke-RestMethod -Uri 'https://api.elevenlabs.io/v1/voices' `
    -Headers @{ 'xi-api-key' = $apiKey }
$matches = $response.voices | Where-Object { $_.name -like "*$voiceName*" }
if ($matches.Count -eq 0) {
    Write-Host "ERROR: No ElevenLabs voice matching '$voiceName' found."
    exit 1
} elseif ($matches.Count -gt 1) {
    Write-Host "Multiple voices found — please pick one:"
    $matches | ForEach-Object { Write-Host "  $($_.name) => $($_.voice_id)" }
    exit 1
}
$voiceId = $matches[0].voice_id
Write-Host "Voice resolved: $($matches[0].name) => $voiceId"
```

---

## Step 3 — Extract and inventory embedded MP3s

A `.story` file is a ZIP archive. Extract it, then determine which MP3s are **actually
embedded** in the ZIP (not just referenced by rels). This is the definitive list to convert —
Storyline files sometimes reference audio that is stored in an MP4 container instead, and
those cannot be replaced via ZIP update.

```powershell
$sevenZip = 'C:\Program Files\AMD\CIM\Bin64\7z.exe'
if (-not (Test-Path $sevenZip)) {
    $sevenZip = (Get-ChildItem 'C:\Program Files' -Recurse -Filter '7z.exe' `
        -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if (-not $sevenZip) { Write-Host 'ERROR: 7z.exe not found.'; exit 1 }

& $sevenZip x $storyPath "-o$extractDir" -y | Out-Null

# Get the authoritative list of MP3 entries from the ZIP itself
Add-Type -Assembly System.IO.Compression
Add-Type -Assembly System.IO.Compression.FileSystem

$zipReadOnly = [System.IO.Compression.ZipFile]::OpenRead($storyPath)
$embeddedMp3s = $zipReadOnly.Entries | Where-Object { $_.FullName -like '*.mp3' }
$mp3Map = @{}   # ZIP entry path (forward slashes) => extracted file path
foreach ($entry in $embeddedMp3s) {
    $zipEntryPath = $entry.FullName   # already uses forward slashes
    $extractedPath = Join-Path $extractDir ($entry.FullName -replace '/', '\')
    $mp3Map[$zipEntryPath] = $extractedPath
}
$zipReadOnly.Dispose()

Write-Host "  Embedded MP3s in ZIP: $($mp3Map.Count)"
```

Why this approach: rels files reference all audio that ever played on a slide, but some
files store most audio in an MP4 container embedded in the ZIP. Only the MP3s that are
actual ZIP entries can be swapped in-place. Scanning rels instead of the ZIP leads to
spurious "entry not found" warnings and wasted API calls.

---

## Step 4 — Convert each MP3 via ElevenLabs STS

Use PowerShell `HttpClient` — **not** `curl`. On Windows Git Bash, `curl -F @file` upload
silently fails with HTTP 000.

```powershell
Add-Type -Assembly System.Net.Http

$client = New-Object System.Net.Http.HttpClient
$client.DefaultRequestHeaders.Add('xi-api-key', $apiKey)
$client.DefaultRequestHeaders.Add('Accept', 'audio/mpeg')
$client.Timeout = [System.TimeSpan]::FromSeconds(180)

$conversionMap = @{}
$idx = 0

foreach ($zipEntry in $mp3Map.Keys) {
    $idx++
    $origPath     = $mp3Map[$zipEntry]
    $mp3Name      = Split-Path $origPath -Leaf
    $convertedPath = Join-Path $convertDir "vc_${idx}_${mp3Name}"

    if (-not (Test-Path $origPath)) {
        Write-Host "  SKIP $mp3Name (not found in extracted archive)"
        continue
    }

    $converted = $false
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        try {
            $form   = New-Object System.Net.Http.MultipartFormDataContent
            $stream = [System.IO.File]::OpenRead($origPath)
            $ac     = New-Object System.Net.Http.StreamContent($stream)
            $ac.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('audio/mpeg')
            $form.Add($ac, 'audio', $mp3Name)
            $form.Add((New-Object System.Net.Http.StringContent('eleven_english_sts_v2')), 'model_id')

            $response = $client.PostAsync(
                "https://api.elevenlabs.io/v1/speech-to-speech/$voiceId", $form).Result
            $stream.Close()
            $form.Dispose()

            if ($response.IsSuccessStatusCode) {
                $bytes = $response.Content.ReadAsByteArrayAsync().Result
                [System.IO.File]::WriteAllBytes($convertedPath, $bytes)
                $sizeKB = [math]::Round($bytes.Length / 1KB, 1)
                Write-Host "  OK  $mp3Name -> new voice ($sizeKB KB)"
                $conversionMap[$zipEntry] = $convertedPath
                $converted = $true
                break
            } else {
                $err = $response.Content.ReadAsStringAsync().Result
                Write-Host "  ERR $mp3Name attempt $attempt HTTP $([int]$response.StatusCode): $err"
                if ($attempt -lt 2) { Start-Sleep -Seconds 2 }
            }
        } catch {
            Write-Host "  ERR $mp3Name attempt $attempt exception: $_"
            if ($attempt -lt 2) { Start-Sleep -Seconds 2 }
        }
    }

    if (-not $converted) { $script:totalFailed++ }
}
```

Important:
- Model must be `eleven_english_sts_v2` — this is the STS (speech-to-speech) model.
  TTS models will not work here because they generate from text, not from existing audio.
- Reuse **one `HttpClient`** across all files in a batch run. Creating one per file
  exhausts connections on large batches.
- On failure, retry once with a 2-second pause before skipping.

---

## Step 5 — Copy original .story (handling OneDrive/Storyline lock)

The `.story` file may be locked by OneDrive sync or an open Storyline session.
Use `robocopy` which retries automatically:

```powershell
$storyParent = Split-Path $storyPath -Parent
$null = robocopy $storyParent $roboCopyTmp $storyName /NJH /NJS /R:5 /W:5
$workStory = Join-Path $tempBase "sl_vc_${fileIndex}_work.story"
Copy-Item (Join-Path $roboCopyTmp $storyName) $workStory -Force
```

**Never repack the ZIP from scratch.** Repacking with 7-Zip or `ZipFile.CreateFromDirectory`
changes ZIP metadata in ways Storyline rejects. Only in-place replacement preserves
the file format.

---

## Step 6 — Replace MP3 entries in-place

Open the copied original in `Update` mode and swap only the converted audio:

```powershell
$zip = [System.IO.Compression.ZipFile]::Open($workStory, 'Update')

foreach ($zipEntry in $conversionMap.Keys) {
    $existing = $zip.GetEntry($zipEntry)
    if ($existing) {
        $existing.Delete()
        $newEntry  = $zip.CreateEntry($zipEntry, [System.IO.Compression.CompressionLevel]::Optimal)
        $outStream = $newEntry.Open()
        $bytes     = [System.IO.File]::ReadAllBytes($conversionMap[$zipEntry])
        $outStream.Write($bytes, 0, $bytes.Length)
        $outStream.Close()
    }
}

$zip.Dispose()
```

Rules:
- Use `Delete()` + `CreateEntry()`, not `Open()` + truncate — so compressed-size metadata stays correct
- ZIP entry paths use **forward slashes** (`story/media/file.mp3`), never backslashes
- Only MP3 entries are touched — all XML, images, rels, and other media are untouched

---

## Step 7 — Save to output and report

```powershell
$outPath   = Join-Path $outputDir $storyName
Copy-Item $workStory $outPath -Force
$outSizeMB = [math]::Round((Get-Item $outPath).Length / 1MB, 1)
Write-Host "  => Saved: $storyName ($outSizeMB MB) -- $($conversionMap.Count) MP3(s) converted"
```

After all files, print a summary:
- MP3s converted per file
- Any failures (file name + HTTP code or exception message)
- Total: `X MP3s converted, Y failures`
- Output folder path

---

## Step 8 — Cleanup

```powershell
Remove-Item $extractDir  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $convertDir  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $workStory   -Force         -ErrorAction SilentlyContinue
Remove-Item $roboCopyTmp -Recurse -Force -ErrorAction SilentlyContinue
```

`-ErrorAction SilentlyContinue` is intentional — Windows may deny access to files whose
streams weren't fully released. This is harmless; Windows cleans them on reboot.

---

## Batch mode

When the user provides a folder path, process all `.story` files in it:

```powershell
$storyFiles = Get-ChildItem -Path $inputDir -Filter '*.story' | Sort-Object Name
```

Use per-file temp dir IDs (`sl_vc_1_extracted`, `sl_vc_2_extracted`, etc.) to prevent
collisions. Reuse **one `HttpClient`** across the entire batch.

Show per-file progress:
```
=== [2/5] Module 02 - Timing Analysis.story ===
  Embedded MP3s in ZIP: 4
  OK  R5zP6mzUiSHD.mp3 -> new voice (390.4 KB)
  OK  R69JXrNkEY82.mp3 -> new voice (428.8 KB)
  ...
  => Saved: Module 02 - Timing Analysis.story (8.1 MB) -- 4 MP3(s) converted
```

---

## Implementation approach

Write the entire pipeline as a **single PowerShell script** at
`$env:TEMP\sl_voice_change.ps1`, then run it. This avoids Bash variable interpolation
breaking PowerShell `$` syntax, and keeps the logic atomic.

Always write the script using the `Write` tool — never via bash heredoc.

```bash
powershell.exe -ExecutionPolicy Bypass -File "$env:TEMP/sl_voice_change.ps1"
```

---

## Important constraints

| Rule | Reason |
|---|---|
| Ask for API key every time | Security — never persist or reuse credentials |
| Use `HttpClient`, NOT `curl` | `curl -F @file` silently fails on Windows Git Bash (HTTP 000) |
| Source MP3 list from ZIP entries, not rels | Rels reference MP4-embedded audio too; ZIP entries are the only ones replaceable |
| Always wipe temp dirs before starting each file | Prevents prior-session MP3s from being re-converted |
| Use `$env:TEMP`, not `C:\Windows\Temp` | System temp folder denies cleanup; user temp folder doesn't |
| Use in-place ZIP update only | Repacking breaks Storyline's ZIP format validation |
| Use `robocopy` to copy locked files | OneDrive/Storyline holds file locks during sync |
| Use `eleven_english_sts_v2` model | Correct STS model — TTS models need text input, not audio |
| Forward slashes in ZIP entry paths | Backslash paths cause Storyline to reject the file |
| Reuse one `HttpClient` for the batch | Per-file clients exhaust connections on large batches |
| Write PS script via Write tool | Bash heredoc interpolates `$` and breaks PowerShell variables |

---

## Troubleshooting

**HTTP 000 from ElevenLabs**
→ Switch to `HttpClient`. `curl -F @file` is broken in Git Bash on Windows.

**"Invalid or corrupt" error when opening in Storyline**
→ ZIP was repacked from scratch. Use in-place update on the original file (Step 6).

**Original .story file locked**
→ `robocopy` with `/R:5 /W:5` retries automatically (Step 5).

**Voice name not found**
→ Run the voices API (Step 2) and show the user the full list. Or ask them to supply the Voice ID directly.

**HTTP 4xx from ElevenLabs**
→ Invalid or expired API key. Ask the user to verify and re-enter it.

**Null-valued expression exception**
→ Transient stream error. Retry that MP3 once.

**"0 MP3s found" for a file you know has narration**
→ The narration is stored in an MP4 container (`.mpeg` file in the ZIP), not as standalone
MP3 entries. This skill can only replace standalone MP3 entries. The MP4-embedded audio
requires a different approach (extract MP4, re-encode, repack) which is not supported here.
Inform the user and copy the file to output unchanged.
