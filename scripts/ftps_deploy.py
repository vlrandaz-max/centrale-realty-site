"""Upload the site to the web root over explicit FTPS (ftplib only, no extra packages).
Env: FTP_HOST, FTP_USERNAME, FTP_PASSWORD, optional FTP_REMOTE_DIR (default "/"), FTP_TLS_SERVERNAME (name on the server certificate), FORCE=true to re-upload everything.
Never deletes remote files. Skips .git, .github, scripts, .cpanel.yml and README.md."""
import os, ssl, sys, ftplib
HOST = os.environ.get("FTP_HOST", "").strip()
USER = os.environ.get("FTP_USERNAME", "").strip()
PASSWORD = os.environ.get("FTP_PASSWORD", "").rstrip("
")  # a pasted secret often ends with a line break
REMOTE = (os.environ.get("FTP_REMOTE_DIR") or "/").strip() or "/"
FORCE = (os.environ.get("FORCE") or "").lower() == "true"
PORT = int(os.environ.get("FTP_PORT") or 21)
if not (HOST and USER and PASSWORD):
    sys.exit("Missing FTP_HOST / FTP_USERNAME / FTP_PASSWORD secrets (repository Settings > Secrets and variables > Actions).")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".github", "scripts"}
SKIP_FILES = {".cpanel.yml", "README.md"}
if not os.path.isfile(os.path.join(ROOT, "index.html")) or os.path.getsize(os.path.join(ROOT, "index.html")) < 1000:
    sys.exit("Safety stop: index.html is missing or too small; nothing was uploaded.")
files = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in SKIP_DIRS]
    for n in fn:
        if n in SKIP_FILES and dp == ROOT:
            continue
        full = os.path.join(dp, n)
        files.append((full, os.path.relpath(full, ROOT).replace(os.sep, "/")))
ctx = ssl.create_default_context()
if os.environ.get("FTP_INSECURE_TLS", "").lower() == "true":
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ftp = ftplib.FTP_TLS(context=ctx, timeout=60)
ftp.connect(HOST, PORT)
TLS_NAME = (os.environ.get("FTP_TLS_SERVERNAME") or "").strip()
if TLS_NAME:
    ftp.host = TLS_NAME  # verify the certificate against its real name (chain is still fully verified)
ftp.login(USER, PASSWORD)
ftp.prot_p()
ftp.cwd(REMOTE)
made = set()
def ensure_dir(rel):
    if not rel or rel in made:
        return
    parent = rel.rpartition("/")[0]
    ensure_dir(parent)
    try:
        ftp.mkd(rel)
    except ftplib.error_perm:
        pass  # already exists
    made.add(rel)
up = skipped = 0
for full, rel in sorted(files):
    ensure_dir(rel.rpartition("/")[0])
    size = os.path.getsize(full)
    if not FORCE:
        try:
            ftp.voidcmd("TYPE I")
            if ftp.size(rel) == size:
                skipped += 1
                continue
        except ftplib.all_errors:
            pass
    with open(full, "rb") as fh:
        ftp.storbinary("STOR " + rel, fh)
    up += 1
    print("uploaded", rel)
ftp.quit()
print(f"Done: {up} uploaded, {skipped} unchanged.")
