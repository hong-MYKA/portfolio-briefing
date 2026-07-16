# Routineの「Instructions(プロンプト)」欄に、以下をそのまま貼り付けてください

---

あなたは洪命江さんの保有株ポートフォリオのデイリーブリーフィングPDFを作成し、このリポジトリにコミットするタスクを実行する。このプロンプトだけを頼りに、過去の実行履歴なしで完結させること。

## 保有銘柄(固定)
1. eMAXIS Slim全世界株式(オール・カントリー)【0331418A】
2. eMAXIS Slim米国株式(S&P500)【03311187】
3. 楽天・プラス・NASDAQ-100インデックス・ファンド【9I314241】

## 手順

### 0. 実行日の確認(重要・過去に事故あり)
作業を始める前に、必ずセッションのシステムコンテキストに含まれる `currentDate` を確認し、これを「今日の日付」として確定する。
`data/` や `reports/` にある**最新の既存ファイルの日付**を「今日」だと推測してはならない
(過去に、2026-07-15分のレポートが既にあったことから2026-07-16の実行を「重複」と誤認してスキップした事故があった)。
当日分が実行済みかどうかは、`currentDate` から導いたYYYYMMDDに対応する `data/YYYYMMDD.json` と
`reports/portfolio_briefing_YYYYMMDD.pdf` が**その日付ちょうどで**存在するかで判断すること。判断に迷う場合はスキップより実行を優先する。

### 1. 最新価格の取得
各銘柄について、以下の専用URLをWebFetch(またはcurl)で取得する。取得できた基準日/日付を確認し、報告書にその基準日をそのまま明記すること。

1. eMAXIS Slim全世界株式(オール・カントリー)【0331418A】
   GET https://developer.am.mufg.jp/fund_information_latest/association_fund_cd/0331418A
   レスポンスJSONの datasets[0] から nav(基準価額,円), cmp_prev_day(前日比,円), percentage_change(前日比,%), base_date(基準日,YYYYMMDD)を取得。

2. eMAXIS Slim米国株式(S&P500)【03311187】
   GET https://developer.am.mufg.jp/fund_information_latest/association_fund_cd/03311187
   同様に取得。

3. 楽天・プラス・NASDAQ-100インデックス・ファンド【9I314241】
   GET https://www.rakuten-sec.co.jp/web/fund/detail/?ID=JP90C000QF22
   ページ本文中の「基準価額」「前日比」「前日比率」の表記から、基準価額・前日比(円)・前日比率(%)・日付(括弧内のM/D)を抽出する。

   このAPIが失敗する、または応答が空の場合は、以下を代替ソースとして試す(この順で):
   - https://s.kabutan.jp/stocks/8058/ (「現在値」「前日終値」の表記を抽出)
   - https://finance.yahoo.co.jp/quote/8058.T
   - https://minkabu.jp/stock/8058

**基準日の鮮度チェック(重要)**: 取得できたbase_date/日付が、実行日から見て「前営業日」の範囲(週末を挟んでも3日以内が目安)を明らかに超えて古い場合(例: 1週間以上前)、そのデータソースは更新遅延している可能性がある。その場合は無理に新しい値を探し回らず、取得できた最新値をそのまま使い、レポート内(エグゼクティブサマリーの注意書きおよび該当銘柄の詳細セクション)に「取得できた基準日が想定より古く、データ提供元側の更新遅延の可能性がある」旨を必ず明記すること。このRoutineの実行環境にはブラウザ操作(Claude in Chromeに相当する機能)は無いため、それ以上のフォールバックは行わない。
また、為替による評価額への影響の情報も組み込む。

### 2. 関連ニュースの収集
WebSearchツールを使い、当日または前夜(直近24時間程度)の以下の観点のニュースを検索する:
- 世界株式市場全体の動向(全世界株式ファンド向け)
- 米国株式市場・S&P500の動向
- NASDAQ100・半導体/AI関連銘柄の動向
- 為替(円ドル)の動向

これらの中から、保有ポートフォリオへの影響度が大きいと判断される重要ニュースを5件に厳選する。各ニュースについて、日付・出典・見出し・要約(2-3文)・ポートフォリオへの影響コメント・センチメント(警戒/好材料/要注視のいずれか)を整理する。当日または前夜のニュースがどうしても5件に満たない場合は、直近数日以内で影響度の高いものを補って5件にする。

### 3. 今後の動向予測
今後の動向予測を、短期(1週間)、中期(1〜3か月)、長期(1年)に分けて提示。
情報は上記のニュースを参考に、足りない情報はウェブサーチして。

### 4. データファイルの作成
リポジトリ直下の `build_pdf.py` が読み込む `data.json` を、`schema.md`(同リポジトリ内)またはbuild_pdf.py冒頭のdocstringに記載のスキーマに従って作成する。exec_summary(その日の市場全体の要約)、fund_lag_note(基準価額タイムラグに関する注意書き。鮮度チェックで問題が見つかった場合はその旨も含める)、holdings(3銘柄分)、news(5件)を全て埋めること。

### 5. PDFの生成と検証
```
pip install -r requirements.txt --break-system-packages
python3 build_pdf.py data.json reports/portfolio_briefing_YYYYMMDD.pdf
```
(YYYYMMDDは実行日の日付)

生成後は必ず `pdftoppm -png -r 120 reports/portfolio_briefing_YYYYMMDD.pdf /tmp/check` で画像化し、Readツールで少なくとも1ページ目を視覚的に確認して、数字・記号(0-9, +, -, %, ., (), &など)が正しく表示されており、tofu(空白/黒box)になっていないことを検証する。もし文字化けが見つかった場合は、build_pdf.pyのmixed_fontヘルパーが正しく適用されているか確認し、data.json側の文言を調整して再生成する。

### 6. コミットして完了
生成した `reports/portfolio_briefing_YYYYMMDD.pdf` と、その日の `data.json`(`data/YYYYMMDD.json` として保存)をリポジトリにコミットし、pushする。コミットメッセージは `portfolio briefing YYYY-MM-DD` のような形式でよい。

メール送信や外部への通知は行わない。完了条件は、reports/配下にその日のPDFがコミットされていること、および視覚検証を行ったことである。

### 7. Pull Requestの作成とマージ(重要)
reports/へのコミットをpushしたブランチから、mainブランチへのPull Requestを作成し、そのままマージまで完了させること(gh CLIまたは利用可能なGitHubツールを使う)。これにより、毎回手動でPRをマージする必要がなくなる。もし権限不足やその他の理由でマージが完了できない場合は、無理に回避策を取らず、run_summary内にその旨とPRのURLを明記すること。

### 8. メール送信(Zapier経由・直接送信)
mainブランチへのマージが完了した後(必ずマージ後に実行すること。マージ前だとファイルが存在せず404になる)、Zapier連携の「Gmail: Send Email」アクション(gmail_send_email)を使い、以下の内容でメールを送信すること:
- To: akann2622@gmail.com
- 件名: 保有株ポートフォリオ・デイリーブリーフィング YYYY-MM-DD
- 本文: 価格サマリーと重要ニュースの要点を簡潔にまとめたもの
- 添付(fileパラメータ): https://raw.githubusercontent.com/hong-MYKA/portfolio-briefing/main/reports/portfolio_briefing_YYYYMMDD.pdf
  (このURLをそのまま渡すこと。base64化やダウンロードは不要)

送信後、結果を確認し、失敗した場合はエラー内容をrun_summaryに明記すること。
