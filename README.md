# 保有株ポートフォリオ・デイリーブリーフィング(Remote Routine版)

Coworkのローカルスケジュールタスクは「PCが起動中・スリープしていない」ことが前提のため、
PCの状態に左右されずに毎日実行したい場合は、Claude Codeの **Remote Routine**(Anthropicのクラウド上で動く仕組み)に移行します。
Remote RoutineはPro以上のプランで利用でき、GitHubリポジトリが必須です。

このフォルダには、そのために必要な一式が入っています。

- `build_pdf.py` … PDF生成スクリプト(data.jsonを読み込んでPDFを作る汎用版)
- `routine_prompt.md` … RoutineのInstructions欄に貼り付けるプロンプト
- `requirements.txt` … 依存パッケージ(reportlab)
- `setup.sh` … Routineの環境設定(Setup script)欄に貼り付ける内容
- `reports/` … 生成されたPDFが毎回コミットされる置き場所(空のままでOK)

## 手順

### 1. GitHubリポジトリを作る

1. https://github.com/new でリポジトリを新規作成(例: `portfolio-briefing`)。Public/Privateどちらでも可(Privateを推奨)。
2. このフォルダの中身(`build_pdf.py`, `routine_prompt.md`, `requirements.txt`, `setup.sh`, `reports/`フォルダ)を、そのリポジトリにアップロードする。
   - gitに慣れていない場合: リポジトリ画面の **Add file > Upload files** から、このフォルダの中身をまとめてドラッグ&ドロップするだけでOK。
   - gitを使う場合:
     ```
     cd portfolio-briefing-routine
     git init
     git remote add origin https://github.com/<あなたのユーザー名>/portfolio-briefing.git
     git add .
     git commit -m "initial commit"
     git branch -M main
     git push -u origin main
     ```

### 2. Routineを作成する

1. Desktopアプリのサイドバーで **Routines** をクリック → **New routine** → **Remote** を選択。
   (**Local**を選ぶと今回問題になったローカルスケジュールタスクになってしまうので注意)
   - もしくは https://claude.ai/code/routines から作成しても同じアカウントに反映されます。
2. **名前**: 「保有株ポートフォリオ・デイリーブリーフィング」など分かりやすい名前を付ける。
3. **プロンプト**: `routine_prompt.md` の中身をそのままコピーして貼り付ける。
4. **リポジトリ**: 手順1で作成した `portfolio-briefing` リポジトリを選択。
5. **環境(Environment)**:
   - Setup scriptに `setup.sh` の中身を貼り付ける(フォントとreportlabを自動インストール)。
   - ネットワークアクセスを **Custom** にし、Allowed domainsに以下を追加(または簡単のため **Full** を選択):
     - `developer.am.mufg.jp`
     - `www.rakuten-sec.co.jp`
     - `query1.finance.yahoo.com`
     - `finance.yahoo.co.jp`
     - `s.kabutan.jp`
     - `minkabu.jp`
6. **トリガー**: Schedule(スケジュール) → 毎日(daily)、希望の時刻(日本時間)を指定。
7. **Permissions**タブで、このリポジトリの **Allow unrestricted branch pushes** を有効にする(mainブランチに直接コミットさせるため。個人用の記録用リポジトリなので問題ありません)。
8. **Create** をクリックして完成。「Run now」で即時テスト実行できます。

### 3. 確認方法

実行が終わると、GitHubリポジトリの `reports/portfolio_briefing_YYYYMMDD.pdf` にその日のPDFがコミットされます。
GitHubのモバイルアプリやブラウザから、PC・スマートフォンいずれでも確認できます。

### 注意点

- メール送信や外部通知は行わない設計です(必要なら別途Slack等のコネクタを追加してください)。
- 投資信託・株価データの基準日が想定より古い場合、レポート内にその旨が明記される設計になっています(実際に前回の実行でも、データ提供元APIの応答が古いという事象が発生しています)。
- Routineはあなたのclaude.aiアカウントの1日あたりの実行回数上限に含まれます。使いすぎには注意してください。
