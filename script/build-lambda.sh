#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pulumi_dir="$repo_root/.pulumi"
bundle_dir="$pulumi_dir/lambda"
deno_version="2.8.1"
deno_archive_name="deno-x86_64-unknown-linux-gnu.zip"
deno_archive_sha256="2d7bb6195226ac832e0bf7109a115f0af65ee69ac797a4bbde5b27a06cc242d9"
deno_download_url="https://github.com/denoland/deno/releases/download/v${deno_version}/${deno_archive_name}"

mkdir -p "$pulumi_dir"
staging_dir="$(mktemp -d "$pulumi_dir/lambda-build.XXXXXX")"
deno_archive="$staging_dir/$deno_archive_name"

cleanup() {
  rm -rf "$staging_dir"
}
trap cleanup EXIT

uv pip install \
  --target "$staging_dir" \
  --requirement "$repo_root/requirements-lambda.txt"

curl --fail --location --retry 3 \
  --output "$deno_archive" \
  "$deno_download_url"
echo "$deno_archive_sha256  $deno_archive" | shasum --algorithm 256 --check
mkdir -p "$staging_dir/bin"
unzip -q "$deno_archive" -d "$staging_dir/bin"
chmod 755 "$staging_dir/bin/deno"
rm "$deno_archive"

cp "$repo_root/handler.py" "$staging_dir/handler.py"
cp -R "$repo_root/notionsyncyoutube" "$staging_dir/notionsyncyoutube"
mkdir -p "$staging_dir/script"
cp "$repo_root/script/fetch-to-notion.py" "$staging_dir/script/fetch-to-notion.py"

rm -rf "$bundle_dir"
mv "$staging_dir" "$bundle_dir"
trap - EXIT

echo "Lambda bundle ready: $bundle_dir"
