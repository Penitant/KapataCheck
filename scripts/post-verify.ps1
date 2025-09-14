<#
Posts two files to the running backend /verify and prints a summary.
Uses MultipartFormDataContent to support multiple files with the same field name 'files'.
#>
param(
  [string]$Url = "http://127.0.0.1:5000/verify",
  [string]$FileA = "server/uploads/sample_a.txt",
  [string]$FileB = "server/uploads/sample_b.txt",
  [string]$Model = "all-mpnet-base-v2"
)

if (-not (Test-Path $FileA)) { throw "File not found: $FileA" }
if (-not (Test-Path $FileB)) { throw "File not found: $FileB" }

$client = [System.Net.Http.HttpClient]::new()
$form = [System.Net.Http.MultipartFormDataContent]::new()

function Add-FilePart([string]$fieldName, [string]$path, [string]$contentType = "text/plain") {
  [byte[]]$bytes = [System.IO.File]::ReadAllBytes($path)
  $content = [System.Net.Http.ByteArrayContent]::new($bytes)
  $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($contentType)
  $fileName = [System.IO.Path]::GetFileName($path)
  $form.Add($content, $fieldName, $fileName)
}

Add-FilePart -fieldName 'files' -path $FileA
Add-FilePart -fieldName 'files' -path $FileB

# Ensure absolute URL and compose query safely
try {
  $baseUri = [System.Uri]::new($Url)
  if (-not $baseUri.IsAbsoluteUri) { throw "Invalid URL (not absolute): $Url" }
} catch {
  throw "Invalid URL: $Url"
}

$builder = [System.UriBuilder]::new($baseUri)
if ([string]::IsNullOrWhiteSpace($builder.Query)) {
  $builder.Query = "model=$Model"
} else {
  $q = $builder.Query.TrimStart('?')
  $builder.Query = "$q&model=$Model"
}
$finalUri = $builder.Uri

$resp = $client.PostAsync($finalUri, $form).Result
$body = $resp.Content.ReadAsStringAsync().Result

if (-not $resp.IsSuccessStatusCode) {
  Write-Error "HTTP $($resp.StatusCode) $($resp.ReasonPhrase): $body"
  exit 1
}

$response = $body | ConvertFrom-Json
"Model: $($response.model)"
"Count: $($response.count)"
foreach ($r in $response.results) {
  "`n$($r.file1) vs $($r.file2)"
  "jaccard=$($r.jaccard), ngram=$($r.ngram), tfidf=$($r.tfidf), paraphrase=$($r.paraphrase)"
  if ($r.PSObject.Properties.Name -contains 'learned_prob') {
    "learned_prob=$($r.learned_prob), learned_risk=$($r.learned_risk)"
  }
  "score=$($r.score), risk=$($r.risk)"
}
