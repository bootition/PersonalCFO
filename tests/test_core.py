#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核心纯函数单元测试

这些函数是"胶水层"里唯一有逻辑的部分：金额解析、journal 解析、
规则分层合成、备份加密往返、期初日期判定。它们出错会**静默**污染账本或报表，
所以必须有测试兜住。

跑：
    venv\\Scripts\\python.exe -m pytest tests -q
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import finance  # noqa: E402
import import_rules  # noqa: E402
import journal_stats  # noqa: E402


# ── 金额解析 ────────────────────────────────────────────────────────────
class TestParseMoneyStrict:
    @pytest.mark.parametrize("text,expected", [
        ("123", 123.0),
        ("1,234.56", 1234.56),
        ("-300", -300.0),
        ("0.01", 0.01),
        ("12,345,678.90", 12345678.90),
        (" 1,000 ", 1000.0),
        # 全角：中文输入法常见，先归一化再校验（此前 Python 接受、Go 拒绝，两层不一致）
        ("１２３", 123.0),
        ("１，２３４．５６", 1234.56),
        ("　１０００　", 1000.0),
    ])
    def test_accepts(self, text, expected):
        assert finance.parse_money_strict(text) == pytest.approx(expected)

    @pytest.mark.parametrize("text", [
        "1,2",          # 千分位不合法（红队明确要求拒绝）
        "1.2.3",
        "abc",
        "",             # 空串
        "1 234",        # 空格分隔
        "1,234.5.6",
        "--1",
        "1e5",
    ])
    def test_rejects(self, text):
        with pytest.raises(ValueError):
            finance.parse_money_strict(text)


# ── journal 解析 ────────────────────────────────────────────────────────
SAMPLE = """\
1970/01/01 * Open Balance
    Assets:FIXME     0 CNY
    Equity:Opening Balances     0 CNY

2026-01-05 * 早餐
    ; orderId: "2026010500001"
    Expenses:日常三餐    12.50 CNY
    Assets:现金:微信    -12.50 CNY

2026-01-06 * 工资
    Assets:现金:工商银行    8000 CNY
    Income:主营收入:工资    -8000 CNY
"""


def _write(tmp_path, text, name="t.journal"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


class TestParseJournal:
    def test_skips_open_balance(self, tmp_path):
        txs = journal_stats.parse_journal(_write(tmp_path, SAMPLE))
        assert len(txs) == 2, "Open Balance 献祭交易必须被跳过"
        assert [t["head"].split()[0] for t in txs] == ["2026-01-05", "2026-01-06"]

    def test_postings_and_amounts(self, tmp_path):
        txs = journal_stats.parse_journal(_write(tmp_path, SAMPLE))
        first = txs[0]
        assert len(first["postings"]) == 2
        accounts = [a for a, _ in first["postings"]]
        assert accounts == ["Expenses:日常三餐", "Assets:现金:微信"]
        assert dict(first["postings"])["Expenses:日常三餐"] == pytest.approx(12.50)

    def test_stats_counts_and_fixme(self, tmp_path):
        p = _write(tmp_path, SAMPLE)
        s = journal_stats.journal_stats(p)
        assert s["txs"] == 2
        assert s["fixme_txs"] == 0


# ── 规则分层合成 ────────────────────────────────────────────────────────
class TestImportRules:
    def test_base_only_when_no_local(self, tmp_path):
        (tmp_path / "alipay.yaml").write_text(
            "defaultCurrency: CNY\nalipay:\n  rules:\n    - item: a\n", encoding="utf-8")
        out = import_rules.merged_config("alipay", base_dir=tmp_path)
        assert out == tmp_path / "alipay.yaml", "无本地覆盖时应直接用公共模板"

    def test_local_rules_appended_last(self, tmp_path):
        (tmp_path / "alipay.yaml").write_text(
            "defaultCurrency: CNY\nalipay:\n  rules:\n    - item: base\n", encoding="utf-8")
        (tmp_path / "alipay.local.yaml").write_text(
            "alipay:\n  rules:\n    - item: local\n", encoding="utf-8")
        out = import_rules.merged_config("alipay", base_dir=tmp_path)
        assert out.name == ".merged-alipay.yaml"

        import yaml
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        rules = doc["alipay"]["rules"]
        # deg 是"后命中覆盖先命中"，所以本地规则必须在最后
        assert rules == [{"item": "base"}, {"item": "local"}]

    def test_top_level_scalar_override(self, tmp_path):
        (tmp_path / "wechat.yaml").write_text(
            "defaultPlusAccount: Expenses:FIXME\nwechat:\n  rules: []\n", encoding="utf-8")
        (tmp_path / "wechat.local.yaml").write_text(
            "defaultPlusAccount: Expenses:其他\nwechat:\n  rules: []\n", encoding="utf-8")
        import yaml
        out = import_rules.merged_config("wechat", base_dir=tmp_path)
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert doc["defaultPlusAccount"] == "Expenses:其他"


# ── 期初日期判定（报表期次门禁的正确性依赖它）────────────────────────────
class TestOpeningDate:
    def test_none_when_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(finance, "JOURNALS_DIR", tmp_path)
        assert finance.opening_date() is None

    def test_latest_of_multiple(self, tmp_path, monkeypatch):
        monkeypatch.setattr(finance, "JOURNALS_DIR", tmp_path)
        (tmp_path / "2026-01-01-opening.journal").write_text(
            "2026-01-01 * 期初\n    Assets:现金    1 CNY\n    Equity:期初调整    -1 CNY\n",
            encoding="utf-8")
        (tmp_path / "2026-09-10-opening.journal").write_text(
            "2026-09-10 * 期初\n    Assets:现金    2 CNY\n    Equity:期初调整    -2 CNY\n",
            encoding="utf-8")
        assert finance.opening_date().isoformat() == "2026-09-10"


# ── 备份：加密往返（golden test）─────────────────────────────────────────
class TestBackupCrypto:
    def test_roundtrip(self, monkeypatch, tmp_path):
        import backup

        secret = tmp_path / "secret.txt"
        monkeypatch.setattr(backup, "SECRET_FILE", secret)
        secret.write_text("test-password-12345", encoding="utf-8")

        class Args:
            password = None

        pw = backup.load_password(Args())

        payload = b"journal contents \xe4\xb8\xad\xe6\x96\x87"
        salt, nonce = b"0" * 16, b"1" * 12
        import hashlib
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, backup.ITERATIONS, dklen=32)
        ct = AESGCM(key).encrypt(nonce, payload, backup.MAGIC)
        blob = backup.MAGIC + salt + nonce + ct

        # 用同一口令能解回来
        key2 = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, backup.ITERATIONS, dklen=32)
        assert AESGCM(key2).decrypt(nonce, ct, backup.MAGIC) == payload

    def test_iterations_not_weakened(self):
        import backup
        assert backup.ITERATIONS >= 600_000, "PBKDF2 迭代数不得低于 600k"

    def test_verify_does_not_create_key(self, monkeypatch, tmp_path):
        """只读命令绝不能凭空生成新密钥（会把"密钥丢失"伪装成"密码错误"）。"""
        import backup
        monkeypatch.setattr(backup, "SECRET_FILE", tmp_path / "does-not-exist.txt")

        class Args:
            password = None

        with pytest.raises(SystemExit):
            backup.load_password(Args(), create=False)
        assert not (tmp_path / "does-not-exist.txt").exists(), "verify/restore 不得落盘新密钥"


# ── 隐私门禁自身 ────────────────────────────────────────────────────────
class TestScanPii:
    def test_generic_patterns_catch_amount_and_id(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "scanpii", ROOT / "scripts" / "scan-pii.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        # 金额用拼接构造：避免字面量被 git filter-repo --replace-text 改写
        amount = "9" + ",876.54" + " 元"
        hits = m.scan_text("本期支出 " + amount, "x.md", [])
        assert any(h[0] == "PII-1" for h in hits), "千分位金额应被拦下"

        hits = m.scan_text("身份证 110101199003071234", "x.md", [])  # pii-ok 假证件号（测试门禁自身）
        assert any(h[0] == "PII-3" for h in hits)

        # 中文路径（假路径，用于验证 PII-7 生效）
        hits = m.scan_text(r"路径 D:\某用户\某目录\账单", "x.md", [])  # pii-ok 假路径
        assert any(h[0] == "PII-7" for h in hits)

    def test_exempt_marker(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "scanpii", ROOT / "scripts" / "scan-pii.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        assert m.scan_text("示例 1,234.56 元  pii-ok", "x.md", []) == []

    def test_placeholder_secret_not_flagged(self):
        """字段名/占位符/正则示例不该被误报（否则 CI 天天红）。"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "scanpii", ROOT / "scripts" / "scan-pii.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for text in [
            'huabei_pdf_password: "..."',
            r"huabei_pdf_password:\s*[\"']?([^\"'\s]+)",
            "config/backup_secret.txt",
        ]:
            assert not [h for h in m.scan_text(text, "x.py", []) if h[0] == "SEC-5"], text
