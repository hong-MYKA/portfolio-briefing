#!/bin/bash
# Routineの「環境(Environment)」設定 > Setup script にこの内容を貼り付けてください。
# 日本語フォント(Droid Sans Fallback)とLatin数字/記号用フォント(Liberation Sans)、
# PDF検証用のpoppler-utils(pdftoppm)をインストールします。
set -e
apt-get update -qq
apt-get install -y -qq fonts-droid-fallback fonts-liberation poppler-utils
pip install --break-system-packages -r requirements.txt
