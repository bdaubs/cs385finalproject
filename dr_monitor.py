#!/usr/bin/env python3

import time
import subprocess
import threading
import requests
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

import boto3

# =========================
# CONFIG
# =========================
CHECK_URL = "http://192.168.56.10/health.php"
EXPECTED_TEXT = "php-site-ok"
CHECK_INTERVAL = 30
REQUEST_TIMEOUT = 5
FAILURES_BEFORE_RECOVERY = 3

TERRAFORM_DIR = Path("/mnt/c/Users/bdaub/dr-terraform")
RUN_TERRAFORM_INIT_EACH_TIME = False

HOSTED_ZONE_ID = "Z1047558143HPZ5J6T70O"
RECORD_NAME = "www.cs385finalproject.com"
NGROK_CNAME_TARGET = "2pog7huktbophmkkc.3a8e3s9715smwpvqi.ngrok-cname.com"
CURRENT_CNAME_TTL = 300
RECOVERY_A_TTL = 60

# =========================
# STATE
# =========================
recovery_in_progress = False
popup_open = False
consecutive_failures = 0
monitoring_active = True


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def site_is_up() -> bool:
    try:
        response = requests.get(CHECK_URL, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            log(f"Health check failed: HTTP {response.status_code}")
            return False

        if EXPECTED_TEXT not in response.text:
            log("Health check failed: expected page text not found.")
            return False

        return True

    except requests.RequestException as e:
        log(f"Health check request failed: {e}")
        return False


def get_terraform_output(output_name: str) -> str:
    result = subprocess.run(
        ["terraform", "output", "-raw", output_name],
        cwd=str(TERRAFORM_DIR),
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def switch_dns_to_recovery(elastic_ip: str):
    log(f"Switching Route 53 record {RECORD_NAME} to recovery IP {elastic_ip}...")

    route53 = boto3.client("route53")

    change_batch = {
        "Comment": "Fail over www to AWS recovery EC2",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {
                    "Name": RECORD_NAME,
                    "Type": "CNAME",
                    "TTL": CURRENT_CNAME_TTL,
                    "ResourceRecords": [
                        {"Value": NGROK_CNAME_TARGET}
                    ]
                }
            },
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": RECORD_NAME,
                    "Type": "A",
                    "TTL": RECOVERY_A_TTL,
                    "ResourceRecords": [
                        {"Value": elastic_ip}
                    ]
                }
            }
        ]
    }

    response = route53.change_resource_record_sets(
        HostedZoneId=HOSTED_ZONE_ID,
        ChangeBatch=change_batch
    )

    change_id = response["ChangeInfo"]["Id"]
    log(f"Route 53 change submitted: {change_id}")


def run_terraform_recovery():
    global recovery_in_progress
    recovery_in_progress = True

    try:
        log("Starting disaster recovery with Terraform...")

        if not TERRAFORM_DIR.exists():
            raise FileNotFoundError(f"Terraform directory not found: {TERRAFORM_DIR}")

        if RUN_TERRAFORM_INIT_EACH_TIME:
            log("Running terraform init...")
            subprocess.run(
                ["terraform", "init"],
                cwd=str(TERRAFORM_DIR),
                check=True
            )

        log("Running terraform apply -auto-approve...")
        subprocess.run(
            ["terraform", "apply", "-auto-approve"],
            cwd=str(TERRAFORM_DIR),
            check=True
        )

        log("Terraform apply completed successfully.")

        recovery_ip = get_terraform_output("dr_public_ip")
        log(f"Terraform reported recovery Elastic IP: {recovery_ip}")

        switch_dns_to_recovery(recovery_ip)

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Recovery Started",
            "Cloud disaster recovery completed.\n\n"
            f"Route 53 is now switching {RECORD_NAME} to {recovery_ip}.\n\n"
            "The AWS recovery site should become reachable after DNS refresh."
        )
        root.destroy()

    except subprocess.CalledProcessError as e:
        log(f"Terraform command failed: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Recovery Failed",
            f"Terraform failed.\n\nError: {e}"
        )
        root.destroy()

    except Exception as e:
        log(f"Unexpected error: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Recovery Failed",
            f"Unexpected error:\n\n{e}"
        )
        root.destroy()

    finally:
        recovery_in_progress = False


def ask_user_to_recover():
    global popup_open, monitoring_active

    if popup_open or recovery_in_progress:
        return

    popup_open = True
    try:
        root = tk.Tk()
        root.withdraw()

        answer = messagebox.askyesno(
            "Disaster Recovery",
            "Website failed 3 health checks in a row.\n\nInitiate cloud disaster recovery?"
        )
        root.destroy()

        if answer:
            log("User chose YES. Stopping monitor and launching recovery...")
            monitoring_active = False
            thread = threading.Thread(target=run_terraform_recovery, daemon=True)
            thread.start()
        else:
            log("User chose NO. Recovery not started.")

    finally:
        popup_open = False


def main():
    global consecutive_failures

    log("Starting DR monitor...")
    log(f"Checking URL: {CHECK_URL}")
    log(f"Expecting text: {EXPECTED_TEXT}")
    log(f"Failures required before recovery prompt: {FAILURES_BEFORE_RECOVERY}")

    while monitoring_active:
        if not recovery_in_progress:
            up = site_is_up()

            if up:
                if consecutive_failures > 0:
                    log("Site recovered. Resetting failure counter.")
                consecutive_failures = 0
                log("Site is healthy.")
            else:
                consecutive_failures += 1
                log(
                    f"Site is unreachable or health check failed. "
                    f"Consecutive failures: {consecutive_failures}/{FAILURES_BEFORE_RECOVERY}"
                )

                if consecutive_failures >= FAILURES_BEFORE_RECOVERY:
                    ask_user_to_recover()
                    consecutive_failures = 0

        time.sleep(CHECK_INTERVAL)

    log("Monitoring stopped after recovery was initiated.")

    # Keep the script alive while the recovery thread finishes
    while recovery_in_progress:
        time.sleep(1)

    log("Recovery thread finished. Exiting monitor.")


if __name__ == "__main__":
    main()
