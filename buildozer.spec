[app]
title = Smart Pacman AI
package.name = smartpacmanai
package.domain = org.smartpacman
source.dir = .
source.include_exts = py,png,jpg,ttf
source.exclude_dirs = tests,bin,.github
source.exclude_patterns = tests.py
version = 1.0
requirements = python3,pygame
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a, armeabi-v7a
android.api = 33
android.minapi = 21
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
