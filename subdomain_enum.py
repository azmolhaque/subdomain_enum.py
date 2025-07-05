import subprocess
import logging
from pathlib import Path

# 🧞 ASCII Gorib greets you!
ASCII_GORIB = r"""
       ___
     _(o o)_
   // \_=_/ \\
  ||  (_)   ||
  || Gorib 🧢||
  ||_______||
   |       |
  /|_______|\
 /_|_______|_\
   ||     ||
  /_\_   _/_\
    /_\ /_\
"""
print(ASCII_GORIB)

# 📝 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("subdomain_enum.log"),
        logging.StreamHandler()
    ]
)

# 📁 Paths
domains_file = Path("domains.txt")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

subfinder_output = output_dir / "subfinder.txt"
amass_output = output_dir / "amass.txt"
assetfinder_output = output_dir / "assetfinder.txt"
combined_output = output_dir / "all_subdomains.txt"
alive_output = output_dir / "subdomains_alive.txt"

def ensure_domains_file():
    if not domains_file.exists() or not domains_file.read_text().strip():
        raise FileNotFoundError("❌ domains.txt not found or is empty.")
    logging.info("✅ domains.txt loaded.")

def run_command(cmd, description):
    try:
        logging.info(f"▶️ Running: {description}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Failed: {description}\n{e}")
        raise

def run_subfinder():
    cmd = ["subfinder", "-dL", str(domains_file), "--all", "--recursive", "-o", str(subfinder_output)]
    run_command(cmd, "Subfinder")

def run_amass():
    temp_output = output_dir / "amass_temp.txt"
    cmd = ["amass", "enum", "-df", str(domains_file), "-o", str(temp_output)]
    try:
        run_command(cmd, "Amass")
        if temp_output.exists() and temp_output.stat().st_size > 0:
            temp_output.replace(amass_output)
            logging.info("✅ Amass results captured.")
        else:
            logging.warning("⚠️ Amass returned no results.")
            temp_output.unlink(missing_ok=True)
    except Exception as e:
        logging.error(f"❌ Amass error: {e}")

def run_assetfinder():
    logging.info("▶️ Running: Assetfinder")
    try:
        with domains_file.open("r") as infile, assetfinder_output.open("w") as outfile:
            for domain in infile:
                domain = domain.strip()
                if domain:
                    try:
                        result = subprocess.check_output(
                            ["assetfinder", "--subs-only", domain],
                            stderr=subprocess.DEVNULL,
                            text=True
                        )
                        outfile.write(result)
                    except subprocess.CalledProcessError:
                        logging.warning(f"⚠️ Assetfinder failed for: {domain}")
    except Exception as e:
        logging.error(f"❌ Assetfinder error: {e}")

def merge_results():
    logging.info("🔀 Merging subdomain results...")
    seen = set()
    with combined_output.open("w") as outfile:
        for result_file in [subfinder_output, amass_output, assetfinder_output]:
            if result_file.exists():
                with result_file.open("r") as infile:
                    for line in infile:
                        sub = line.strip()
                        if sub and sub not in seen:
                            seen.add(sub)
                            outfile.write(sub + "\n")
    logging.info(f"✅ All subdomains saved in: {combined_output}")

def run_httpx():
    if not combined_output.exists() or not combined_output.read_text().strip():
        logging.warning("⚠️ No subdomains to probe with httpx.")
        return
    cmd = ["httpx", "-l", str(combined_output), "-silent", "-o", str(alive_output)]
    run_command(cmd, "Httpx")
    logging.info(f"✅ Alive subdomains saved in: {alive_output}")

def cleanup():
    logging.info("🧹 Cleaning up intermediate files...")
    for f in [subfinder_output, amass_output, assetfinder_output]:
        try:
            if f.exists():
                f.unlink()
                logging.info(f"🗑️ Removed: {f}")
        except Exception as e:
            logging.warning(f"⚠️ Could not delete {f}: {e}")

def main():
    try:
        ensure_domains_file()
        run_subfinder()
        run_amass()
        run_assetfinder()
        merge_results()
        run_httpx()
        cleanup()
        logging.info("🎯 Enumeration complete! Alive subdomains stored in: %s", alive_output)
    except FileNotFoundError as fnf:
        logging.error(fnf)
    except Exception as ex:
        logging.exception(f"❌ Unhandled error: {ex}")

if __name__ == "__main__":
    main()
