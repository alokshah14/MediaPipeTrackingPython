# Distribution Guide - How to Share Your App

This guide explains the easiest ways to distribute Finger Invaders to Windows users **without requiring Python, Git, or any technical setup**.

---

## ⭐ OPTION 1: GitHub Releases (Recommended - Fully Automated)

**Best for:** Sharing with researchers, testers, or public distribution

### How it Works:
1. Push a version tag to GitHub (e.g., `v1.0.0`)
2. GitHub Actions automatically builds the Windows executable
3. A release is created with a downloadable zip file
4. Users download and run - **no building required!**

### Setup Steps:

1. **One-time: Enable GitHub Actions**
   - The workflow file is already created at `.github/workflows/build-release.yml`
   - GitHub Actions should work automatically on your repo

2. **Create a Release:**
   ```bash
   # On your Mac or any machine with git
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **Wait ~10 minutes** for GitHub to build

4. **Share the link:**
   ```
   https://github.com/alokshah14/LeapTrackingPython/releases/latest
   ```

### What Users Get:
- Direct download link for `FingerInvaders-Windows.zip`
- Extract and run `FingerInvaders.exe`
- **No Python, Git, or build tools needed!**

---

## 💾 OPTION 2: Manual Zip File (Simple)

**Best for:** Quick sharing via email or Dropbox

### On a Windows Machine (One Time):

1. **Install prerequisites** (only needed once):
   ```powershell
   # Install Python from python.org
   # Install Ultraleap SDK
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Build the executable:**
   ```bash
   build-windows.bat
   ```

3. **Create zip file:**
   - Go to `dist\FingerInvaders\`
   - Right-click → Send to → Compressed (zipped) folder
   - Name it `FingerInvaders-v1.0.zip`

4. **Upload to:**
   - Google Drive / Dropbox / OneDrive
   - Email (if under 25MB)
   - File sharing service

5. **Share the link** with instructions:
   ```
   1. Download FingerInvaders-v1.0.zip
   2. Extract the zip file
   3. Install Ultraleap Hand Tracking from: https://leap2.ultraleap.com/downloads/
   4. Run FingerInvaders.exe
   ```

---

## 📦 OPTION 3: Windows Installer (Most Professional)

**Best for:** Formal distribution or non-technical users

### Setup:

1. **Download Inno Setup** (free):
   ```
   https://jrsoftware.org/isdl.php
   ```

2. **Build the executable first:**
   ```bash
   build-windows.bat
   ```

3. **Create installer:**
   - Open Inno Setup
   - Load `installer.iss`
   - Click Build → Compile
   - Find `installer_output\FingerInvaders-Setup.exe`

4. **Distribute the installer:**
   - Users just run `FingerInvaders-Setup.exe`
   - Automatic desktop shortcut
   - Proper uninstaller
   - Checks for Ultraleap SDK

---

## 🎮 OPTION 4: Cloud Build (No Windows Machine Needed)

**Best for:** Building from Mac without accessing Windows

### Use GitHub Actions (Already Set Up):

Just push a tag and let GitHub build it:
```bash
git tag v1.0.0
git push origin v1.0.0
```

Download the built executable from:
```
https://github.com/YOUR_USERNAME/LeapTrackingPython/releases/tag/v1.0.0
```

---

## 📋 What to Tell Users

### Minimum Requirements:
- Windows 10/11 (64-bit)
- 4GB RAM
- Ultraleap Hand Tracking Service installed

### Quick Start Instructions:
```
1. Download FingerInvaders-Windows.zip
2. Extract to any folder
3. Install Ultraleap Hand Tracking:
   https://leap2.ultraleap.com/downloads/
4. Make sure the Ultraleap service is running (green icon in system tray)
5. Run FingerInvaders.exe
```

### For Testing Without Leap Device:
```
FingerInvaders.exe --simulation
```
Then use keyboard:
- Left hand: Q W E R T
- Right hand: Y U I O P

---

## 📊 Comparison

| Method | Setup Effort | User Experience | Best For |
|--------|--------------|-----------------|----------|
| GitHub Releases | ⭐ Low (automated) | ⭐⭐⭐ Best | Public/research distribution |
| Manual Zip | ⭐⭐ Medium (one-time) | ⭐⭐ Good | Quick sharing |
| Installer | ⭐⭐⭐ High (one-time) | ⭐⭐⭐ Best | Professional distribution |
| Cloud Build | ⭐ Low (automated) | ⭐⭐⭐ Best | Mac-only developers |

---

## ✅ Recommended Workflow

**For you (developer):**
1. Use **GitHub Releases** (Option 1) - fully automated
2. Just push version tags when ready to release
3. Share the GitHub releases link

**For end users:**
1. Click download link
2. Extract zip
3. Run exe
4. Done! 🎉

**No Git, Python, or technical knowledge required on their end!**
