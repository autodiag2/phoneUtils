import zipfile, os, tempfile, tkinter as tk, sys, subprocess, datetime

def adb_root():
    subprocess.run(["adb", "root"], capture_output=True)

def adb_apk_location_from(package_name):
    adb_root()
    r = subprocess.run(
        ["adb", "shell", "pm", "path", package_name], capture_output=True, text=True
    )
    if r.returncode != 0 or not r.stdout.startswith("package:"):
        return None
    apk_path = r.stdout.strip().split("package:")[-1]
    return apk_path

def adb_android_codename():
    adb_root()
    r = subprocess.run(["adb", "shell", "getprop", "ro.build.version.codename"], capture_output=True, text=True)
    if r.returncode != 0:
        return "unknown"
    return r.stdout.strip()

def adb_exec(cmd):
    adb_root()
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout if r.returncode == 0 else b''

def adb_check_rw(path):
    adb_root()
    test_cmd=f"touch '{path}/.rwtest' && rm '{path}/.rwtest'"
    r=subprocess.run(['adb','shell',test_cmd],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return r.returncode==0

def adb_ensure_folder_writable(path):
    adb_root()
    if adb_check_rw(path):
        return True
    adb_exec(['adb','shell',f'mount -o remount,rw /'])
    adb_exec(['adb','shell',f'mount -o remount,rw /product'])
    return adb_check_rw(path)