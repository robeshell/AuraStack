# AuraStack API 文档

当前模式与 `map1.huodaitianyan.com` 一致：

- `docs/apifox-full.openapi.json` 是接口文档源文件（OpenAPI）
- `backend/scripts/import_openapi_to_apifox.py` 只负责把该文件推送到 Apifox

## 导入到 Apifox（覆盖导入）

先设置环境变量：

```bash
export APIFOX_PROJECT_ID='<你的项目ID>'
export APIFOX_ACCESS_TOKEN='<你的访问令牌>'
```

执行导入：

```bash
./venv/bin/python backend/scripts/import_openapi_to_apifox.py \
  --spec-file docs/apifox-full.openapi.json \
  --endpoint-overwrite-behavior OVERWRITE_EXISTING \
  --schema-overwrite-behavior OVERWRITE_EXISTING
```

如果希望把 Apifox 里“源数据不存在”的接口/模型也删除，可追加：

```bash
--delete-unmatched-resources
```
