import subprocess
import logging
from pathlib import Path

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("subdomain_enum.log"),
        logging.StreamHandler()
    ]
)

# File paths
domains_file = Path("domains.txt")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

subfinder_output = output_dir / "subfinder_results.txt"
amass_output = output_dir / "amass_results.txt"
assetfinder_output = output_dir / "assetfinder_results.txt"
combined_output = output_dir / "combined_subdomains.txt"
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
    run_command(cmd, "subfinder")

def run_amass():
    cmd = ["amass", "enum", "-df", str(domains_file), "-o", str(amass_output)]
    run_command(cmd, "amass")

def run_assetfinder():
    logging.info("▶️ Running: assetfinder")
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
        logging.error(f"❌ Error in assetfinder block: {e}")
        raise

def merge_results():
    logging.info("🔀 Merging results...")
    seen = set()
    with combined_output.open("w") as outfile:
        for result_file in [subfinder_output, amass_output, assetfinder_output]:
            if not result_file.exists():
                continue
            with result_file.open("r") as infile:
                for line in infile:
                    sub = line.strip()
                    if sub and sub not in seen:
                        seen.add(sub)
                        outfile.write(sub + "\n")
    logging.info(f"✅ Combined subdomains written to: {combined_output}")

def run_httpx():
    if not combined_output.exists() or not combined_output.read_text().strip():
        logging.warning("⚠️ No subdomains to probe with httpx.")
        return
    cmd = ["httpx", "-l", str(combined_output), "-silent", "-o", str(alive_output)]
    run_command(cmd, "httpx")
    logging.info(f"✅ Alive subdomains saved to: {alive_output}")

def cleanup_files():
    logging.info("🧹 Cleaning up intermediate files...")
    for f in [subfinder_output, amass_output, assetfinder_output, combined_output]:
        try:
            if f.exists():
                f.unlink()
                logging.info(f"🗑️ Deleted: {f}")
        except Exception as e:
            logging.warning(f"❌ Could not delete {f}: {e}")

def main():
    try:
        ensure_domains_file()
        run_subfinder()
        run_amass()
        run_assetfinder()
        merge_results()
        run_httpx()
        cleanup_files()
        logging.info("🎉 All done. Final results in: %s", alive_output)
    except FileNotFoundError as fnf:
        logging.error(fnf)
    except Exception as ex:
        logging.exception(f"❌ Unhandled exception: {ex}")

if __name__ == "__main__":
    main()
