# dbt-insight-mcp-server

dbt CloudのジョブやプロジェクトをClaude経由で管理・実行するためのModel Context Protocol (MCP) サーバーです。ジョブの検索、実行履歴確認、ジョブのトリガーなどが可能です。

**使用API:** dbt Cloud API v2（ジョブ・ラン操作用）  
**Note:** API v3は管理操作用のため、実行操作にはv2を使用

## 安全機能

- **ガードレール**: 危険な操作には必ず確認が必要
- **段階的確認**: `run`や`test`操作は明示的な確認なしには実行されません
- **読み取り専用優先**: 検索とプレビューは安全な読み取り専用操作
- **操作の可視化**: 実行される操作の詳細を事前に表示

## 機能

### 読み取り専用操作（確認不要）
- **プロジェクト検索**: ジョブやプロジェクトの検索
- **ジョブ一覧**: dbtジョブの一覧表示
- **実行履歴**: 最近のジョブ実行履歴の確認
- **プロジェクト一覧**: 利用可能なプロジェクトの表示

### 実行操作（確認必須）
- **ジョブ実行**: dbt Cloudジョブのトリガー（データ変更・コスト発生の可能性）

## 利用可能なツール

### 1. `search_in_project`
プロジェクト内のジョブを検索します。

**パラメータ:**
- `query`: 検索クエリ（ジョブ名や説明）
- `project_id`: プロジェクトID

### 2. `get_recent_runs`
最近のジョブ実行履歴を取得します。

**パラメータ:**
- `project_id`: プロジェクトID
- `limit`: 取得件数（1-50、デフォルト: 10）

### 3. `list_projects`
利用可能なdbtプロジェクトを一覧表示します。

### 4. `list_jobs`
dbtジョブを一覧表示します。

**パラメータ:**
- `project_id`: フィルターするプロジェクトID

### 5. `trigger_job_with_confirmation`
**注意**: dbt Cloudジョブを実行します（データ変更・コスト発生の可能性）

**パラメータ:**
- `job_id`: 実行するジョブID
- `cause`: 実行理由（デフォルト: "Triggered via MCP"）
- `confirm_execution`: **必ずtrueに設定して確認**

## インストール

1. このリポジトリをクローン:
```bash
git clone https://github.com/yourusername/dbt-insight-mcp-server.git
cd dbt-insight-mcp-server
```

2. 環境変数を設定:
```bash
cp .env.example .env
# .envファイルを編集してdbt Cloudの接続情報を入力
```

3. セットアップスクリプトを実行:
```bash
./setup.sh
```

## 設定

### 環境変数

`.env`ファイルに以下の設定が必要です：

```env
# dbt Cloud API Token (必須)
DBT_API_TOKEN=your-dbt-api-token-here

# dbt Cloud Account ID (必須)
DBT_ACCOUNT_ID=your-account-id-here

# dbt Cloud Base URL (オプション)
DBT_BASE_URL=https://cloud.getdbt.com
```

### Claude Desktop設定

Claude Desktop設定ファイルに以下を追加してください:

```json
{
  "mcpServers": {
    "dbt-insight": {
      "command": "/path/to/dbt-insight-mcp-server/venv/bin/python",
      "args": ["/path/to/dbt-insight-mcp-server/server.py"]
    }
  }
}
```

## dbt Cloud APIトークンの取得

1. dbt Cloudにログイン
2. Account Settings → API Access
3. "Generate New Token"をクリック
4. 適切な権限を設定（Account AdminまたはProject権限）
5. トークンをコピーして`.env`ファイルに設定

## 地域別設定

### 日本インスタンス
```env
DBT_BASE_URL=https://your-instance.jp1.dbt.com
DBT_ACCOUNT_ID=your-account-id
DBT_API_TOKEN=dbtc_your-token
```

### US インスタンス
```env
DBT_BASE_URL=https://cloud.getdbt.com
DBT_ACCOUNT_ID=your-account-id
DBT_API_TOKEN=dbtc_your-token
```

## 安全性に関する重要な注意

このMCPサーバーは以下の安全機能を提供します：

1. **確認必須操作**: `run`や`test`は明示的な確認なしには実行されません
2. **操作の透明性**: 実行前に操作の詳細が表示されます
3. **読み取り専用優先**: 検索やプレビューは安全な読み取り専用操作
4. **ガードレール**: 危険な操作をブロックし、確認を求めます

**重要**: `confirm_execution=true`を設定する前に、操作の影響を必ず理解してください。

## 使用例

### 基本的な操作
```
# ジョブの一覧を表示
"プロジェクトのジョブ一覧を見せて"

# 特定のジョブを検索
"buildというジョブを検索して"

# 最近の実行履歴を確認
"最近のジョブ実行履歴を教えて"

# プロジェクト一覧を表示
"利用可能なプロジェクトを教えて"
```

### ジョブ実行（危険操作）
```
# 確認が必要な操作
"sample_jobを実行して（ジョブID: 123456）"
→ 最初は確認なしでブロックされます

# 確認付きで実行
"sample_jobを実行して（confirm_execution: true）"
→ 実際にジョブが実行されます
```

## 必要条件

- Python 3.10+
- dbt Cloud アカウント
- 有効なdbt Cloud APIトークン
- Claude Desktop

## ライセンス

MIT License
